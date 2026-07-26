"""MadGraph5 -> Pythia8 -> Delphes -> EDM4hep workflow."""

from __future__ import annotations

import gzip
import json
import os
import secrets
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lhapdf import prepare_lhapdf
from parsers import (
    load_manifest,
    matching_description,
    parse_lhe,
    parse_madgraph_card,
    parse_podio_event_count,
    patch_delphes_seed,
    render_template,
)


# Compatibility path required by MadGraph helpers in Key4hep 2026-04-08.
KEY4HEP_YAML_CPP = Path(
    "/cvmfs/sw.hsf.org/key4hep/releases/2026-02-01/"
    "x86_64-almalinux9-gcc14.2.0-opt/"
    "yaml-cpp/0.8.0-v762up/lib64"
)


@dataclass(frozen=True)
class WorkflowOptions:
    config_file: Path
    prepare: bool
    dry_run: bool
    confirm: bool
    overwrite: bool
    keep_lhe: bool
    keep_work: bool
    lhapdf_directory: Path


def run_fcc_workflow(options: WorkflowOptions) -> int:
    config_file = options.config_file.expanduser().resolve()
    if not config_file.is_file():
        raise RuntimeError(f"Configuration was not found: {config_file}")

    base = config_file.parent
    manifest = load_manifest(config_file)
    cards = {
        name: resolve_card(manifest[f"{name}_card"], base)
        for name in ("madgraph", "pythia", "delphes", "edm4hep")
    }
    mg = parse_madgraph_card(cards["madgraph"])

    process_dir = (base / mg["output_directory"]).resolve()
    output_dir = base / "outputs"
    root_file = output_dir / f"{mg['sample_name']}.root"
    metadata_file = output_dir / f"{mg['sample_name']}.metadata.json"
    lhe_output = output_dir / f"{mg['sample_name']}.lhe.gz"

    commands = {
        name: require_command(name)
        for name in ("mg5_aMC", "DelphesPythia8_EDM4HEP", "podio-dump")
    }

    environment = dict(os.environ)
    if KEY4HEP_YAML_CPP.is_dir():
        old_path = environment.get("LD_LIBRARY_PATH", "")
        environment["LD_LIBRARY_PATH"] = (
            f"{KEY4HEP_YAML_CPP}{os.pathsep}{old_path}"
            if old_path
            else str(KEY4HEP_YAML_CPP)
        )

    pdf = prepare_lhapdf(
        mg["lhaid"],
        options.lhapdf_directory,
        environment,
        install=False,
    )
    print_summary(cards, mg, pdf, root_file)

    if options.dry_run:
        print("\nDry run completed. No files were generated.")
        return 0

    if options.confirm:
        if not sys.stdin.isatty():
            raise RuntimeError("--confirm requires an interactive terminal.")
        input("\nPress Enter to start or Ctrl+C to cancel: ")

    pdf = prepare_lhapdf(
        mg["lhaid"],
        options.lhapdf_directory,
        environment,
        install=True,
    )
    if options.prepare:
        name = pdf["name"] if pdf else "No PDF requested"
        print(f"\nEnvironment preparation completed: {name}")
        return 0

    if root_file.exists() and not options.overwrite:
        raise RuntimeError(
            f"Output already exists: {root_file}\n"
            "Use --overwrite to replace it after successful validation."
        )
    if process_dir.exists():
        raise RuntimeError(
            f"MadGraph output directory already exists: {process_dir}"
        )

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_dir = base / "logs" / mg["sample_name"] / run_id
    log_dir.mkdir(parents=True)
    shutil.copy2(config_file, log_dir / "config.yaml")
    for name in ("madgraph", "pythia"):
        shutil.copy2(cards[name], log_dir / cards[name].name)

    output_dir.mkdir(parents=True, exist_ok=True)
    temporary_root = output_dir / f".{mg['sample_name']}.{run_id}.root"
    success = False

    try:
        print("\n[1/3] Running MadGraph5...")
        run_command(
            [commands["mg5_aMC"], str(cards["madgraph"])],
            log_dir / "madgraph.log",
            base,
            environment,
        )

        lhe_source = find_lhe(process_dir)
        lhe_file = process_dir / "Events" / "fcc_runner_events.lhe"
        unpack_lhe(lhe_source, lhe_file)
        lhe = parse_lhe(lhe_file)
        if lhe["events"] < 1:
            raise RuntimeError(f"The LHE file contains no events: {lhe_file}")

        seeds = runtime_seeds(mg["iseed"])
        pythia_runtime = log_dir / "pythia_runtime.cmd"
        pythia_runtime.write_text(
            render_template(
                cards["pythia"],
                {
                    "LHE_FILE": lhe_file,
                    "LHE_EVENTS": lhe["events"],
                    "PYTHIA_SEED": seeds["pythia"],
                },
            ),
            encoding="utf-8",
        )

        delphes_runtime = log_dir / "delphes_runtime.tcl"
        delphes_runtime.write_text(
            patch_delphes_seed(cards["delphes"], seeds["delphes"]),
            encoding="utf-8",
        )

        print("\n[2/3] Running Pythia8 and Delphes...")
        run_command(
            [
                commands["DelphesPythia8_EDM4HEP"],
                str(delphes_runtime),
                str(cards["edm4hep"]),
                str(pythia_runtime),
                str(temporary_root),
            ],
            log_dir / "pythia_delphes.log",
            base,
            environment,
        )

        print("\n[3/3] Validating the EDM4hep output...")
        output_events = validate_output(
            temporary_root,
            commands["podio-dump"],
            log_dir / "validation.log",
            environment,
        )

        copy_madgraph_cards(process_dir, lhe_source.parent, log_dir)
        if options.keep_lhe:
            save_lhe(lhe_file, lhe_output)

        metadata = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "sample": mg["sample_name"],
            "requested_events": mg["nevents"],
            "lhe_events": lhe["events"],
            "edm4hep_events": output_events,
            "cross_section_pb": lhe["cross_section_pb"],
            "cross_section_error_pb": lhe["cross_section_error_pb"],
            "beam1_energy_gev": mg["ebeam1"],
            "beam2_energy_gev": mg["ebeam2"],
            "lhaid": mg["lhaid"],
            "matching": matching_description(mg),
            "seeds": seeds,
            "cards": {name: str(path) for name, path in cards.items()},
            "executables": commands,
        }

        os.replace(temporary_root, root_file)
        metadata_file.write_text(
            json.dumps(metadata, indent=2) + "\n",
            encoding="utf-8",
        )
        success = True

        print("\nProduction completed successfully.")
        print(f"EDM4hep output : {root_file}")
        print(f"Metadata       : {metadata_file}")
        print(f"Logs           : {log_dir}")
        return 0

    finally:
        temporary_root.unlink(missing_ok=True)
        if success and not options.keep_work:
            shutil.rmtree(process_dir)
        elif not success and process_dir.exists():
            print(
                f"\nFailed MadGraph directory preserved:\n  {process_dir}",
                file=sys.stderr,
            )


def resolve_card(value: str, base: Path) -> Path:
    path = Path(os.path.expandvars(os.path.expanduser(value)))
    path = path if path.is_absolute() else base / path
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError(f"Card was not found: {path}")
    return path


def require_command(name: str) -> str:
    command = shutil.which(name)
    if command is None:
        raise RuntimeError(
            f"'{name}' was not found. Load Key4hep before running."
        )
    return command


def print_summary(
    cards: dict[str, Path],
    mg: dict[str, Any],
    pdf: dict[str, Any] | None,
    root_file: Path,
) -> None:
    if pdf is None:
        pdf_text = "Not requested"
    elif pdf["name"]:
        status = "installed" if pdf["installed"] else "not installed"
        pdf_text = f"{pdf['lhaid']} ({pdf['name']}, {status})"
    else:
        pdf_text = str(pdf["lhaid"])

    rows = [
        ("MadGraph card", cards["madgraph"]),
        ("Pythia card", cards["pythia"]),
        ("Delphes card", cards["delphes"]),
        ("MG5 output", mg["output_directory"]),
        ("Events", mg["nevents"]),
        ("Beam energies", f"{mg['ebeam1']} + {mg['ebeam2']} GeV"),
        ("LHAPDF", pdf_text),
        ("Jet matching", matching_description(mg)),
        ("Final output", root_file),
    ]
    width = max(len(label) for label, _ in rows)

    print("Production summary")
    print("-" * (width + 2))
    for label, value in rows:
        print(f"{label:<{width}} : {value}")


def run_command(
    command: list[str],
    log_file: Path,
    working_directory: Path,
    environment: dict[str, str],
) -> None:
    with log_file.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=working_directory,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            log.write(line)
        return_code = process.wait()

    if return_code != 0:
        raise RuntimeError(
            f"Command returned {return_code}. See: {log_file}"
        )


def find_lhe(process_dir: Path) -> Path:
    events_dir = process_dir / "Events"
    names = {
        "unweighted_events.lhe.gz",
        "unweighted_events.lhe",
        "events.lhe.gz",
        "events.lhe",
    }
    files = [
        path
        for path in events_dir.rglob("*")
        if path.is_file() and path.name in names
    ] if events_dir.is_dir() else []

    if len(files) != 1:
        raise RuntimeError(
            f"Expected one LHE output in {events_dir}; found {len(files)}."
        )
    return files[0]


def unpack_lhe(source: Path, destination: Path) -> None:
    if source.suffix == ".gz":
        with gzip.open(source, "rb") as input_file:
            with destination.open("wb") as output_file:
                shutil.copyfileobj(input_file, output_file)
    else:
        shutil.copy2(source, destination)


def runtime_seeds(madgraph_seed: int | None) -> dict[str, int | None]:
    base = (
        madgraph_seed
        if madgraph_seed and 1 <= madgraph_seed <= 899_999_997
        else secrets.randbelow(899_999_997) + 1
    )
    return {
        "madgraph": madgraph_seed,
        "pythia": base + 1,
        "delphes": base + 2,
    }


def validate_output(
    root_file: Path,
    podio_dump: str,
    log_file: Path,
    environment: dict[str, str],
) -> int:
    if not root_file.is_file() or root_file.stat().st_size == 0:
        raise RuntimeError(f"EDM4hep output is missing or empty: {root_file}")

    result = subprocess.run(
        [podio_dump, str(root_file)],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    log_file.write_text(result.stdout, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"podio-dump failed. See: {log_file}")

    events = parse_podio_event_count(result.stdout)
    if events < 1:
        raise RuntimeError("The EDM4hep output contains no events.")
    return events


def copy_madgraph_cards(
    process_dir: Path,
    run_dir: Path,
    log_dir: Path,
) -> None:
    for name in ("run_card.dat", "param_card.dat"):
        source = process_dir / "Cards" / name
        if source.is_file():
            shutil.copy2(source, log_dir / name)
    for banner in run_dir.glob("*banner.txt"):
        shutil.copy2(banner, log_dir / banner.name)


def save_lhe(source: Path, destination: Path) -> None:
    temporary = destination.with_name(f".{destination.name}.tmp")
    with source.open("rb") as input_file:
        with gzip.open(temporary, "wb") as output_file:
            shutil.copyfileobj(input_file, output_file)
    os.replace(temporary, destination)