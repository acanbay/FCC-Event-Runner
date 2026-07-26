"""Parsers and text transformations used by the FCC workflow."""

from __future__ import annotations

import math
import re
import shlex
from pathlib import Path
from typing import Any


try:
    import yaml
except ImportError as error:
    raise RuntimeError(
        "The loaded Key4hep Python environment does not provide PyYAML."
    ) from error


TEMPLATE_PATTERN = re.compile(r"@([A-Z][A-Z0-9_]*)@")


def load_manifest(config_file: Path) -> dict[str, str]:
    content = yaml.safe_load(config_file.read_text(encoding="utf-8"))

    if not isinstance(content, dict):
        raise RuntimeError("The YAML root must be a mapping.")

    required_fields = (
        "madgraph_card",
        "pythia_card",
        "delphes_card",
        "edm4hep_card",
    )

    missing_fields = set(required_fields) - set(content)

    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise RuntimeError(f"Missing YAML field(s): {missing}")

    return {
        field: str(content[field])
        for field in required_fields
    }


def parse_madgraph_card(card_file: Path) -> dict[str, Any]:
    output_directory: str | None = None
    settings: dict[str, str] = {}

    for raw_line in card_file.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        line = raw_line.split("#", 1)[0].strip()

        if not line:
            continue

        try:
            fields = shlex.split(line)
        except ValueError:
            continue

        if not fields:
            continue

        command = fields[0].lower()

        if command == "output" and len(fields) >= 2:
            output_directory = fields[1]

        if command == "set" and len(fields) >= 3:
            settings[fields[1].lower()] = fields[2]

    if output_directory is None:
        raise RuntimeError(
            f"No 'output <directory>' command was found in {card_file}."
        )

    output_path = Path(output_directory)

    if output_path.is_absolute() or ".." in output_path.parts:
        raise RuntimeError(
            "The MadGraph output directory must be a safe relative path."
        )

    if output_path in {Path("."), Path("")}:
        raise RuntimeError("The MadGraph output directory is not valid.")

    return {
        "output_directory": output_directory,
        "sample_name": output_path.name,
        "nevents": parse_integer(settings.get("nevents")),
        "iseed": parse_integer(settings.get("iseed")),
        "ebeam1": parse_float(settings.get("ebeam1")),
        "ebeam2": parse_float(settings.get("ebeam2")),
        "lhaid": parse_integer(settings.get("lhaid")),
        "pdlabel": settings.get("pdlabel"),
        "ickkw": parse_integer(settings.get("ickkw"), default=0),
        "xqcut": parse_float(settings.get("xqcut")),
        "maxjetflavor": parse_integer(settings.get("maxjetflavor")),
        "alpsfact": parse_float(settings.get("alpsfact")),
    }


def parse_integer(
    value: str | None,
    default: int | None = None,
) -> int | None:
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def parse_float(
    value: str | None,
    default: float | None = None,
) -> float | None:
    if value is None:
        return default

    try:
        return float(value.replace("D", "E").replace("d", "e"))
    except ValueError:
        return default


def matching_description(madgraph_information: dict[str, Any]) -> str:
    ickkw = madgraph_information.get("ickkw", 0)

    if ickkw == 0:
        return "Disabled"

    if ickkw == 1:
        xqcut = madgraph_information.get("xqcut")

        if xqcut is None:
            return "MLM"

        return f"MLM (xqcut = {xqcut:g} GeV)"

    if ickkw == 3:
        return "FxFx"

    return f"Enabled (ickkw = {ickkw})"


def render_template(
    template_file: Path,
    replacements: dict[str, Any],
) -> str:
    content = template_file.read_text(encoding="utf-8")

    for key, value in replacements.items():
        content = content.replace(f"@{key}@", str(value))

    unresolved = sorted(set(TEMPLATE_PATTERN.findall(content)))

    if unresolved:
        fields = ", ".join(f"@{name}@" for name in unresolved)

        raise RuntimeError(
            f"Unresolved template field(s) in {template_file}: {fields}"
        )

    return content


def patch_delphes_seed(
    delphes_card: Path,
    seed: int,
) -> str:
    content = delphes_card.read_text(encoding="utf-8")
    replacement = f"set RandomSeed {seed}"

    updated_content, replacement_count = re.subn(
        r"(?m)^\s*set\s+RandomSeed\s+\S+\s*$",
        replacement,
        content,
        count=1,
    )

    if replacement_count == 0:
        updated_content = f"{replacement}\n{content}"

    return updated_content


def parse_lhe(lhe_file: Path) -> dict[str, Any]:
    event_count = 0
    init_lines: list[str] = []
    inside_init = False

    with lhe_file.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as stream:
        for raw_line in stream:
            line = raw_line.strip()

            if line.startswith("<event"):
                event_count += 1

            if line.startswith("<init"):
                inside_init = True
                continue

            if line.startswith("</init"):
                inside_init = False
                continue

            if inside_init and line and not line.startswith("#"):
                init_lines.append(line)

    information: dict[str, Any] = {
        "events": event_count,
        "cross_section_pb": None,
        "cross_section_error_pb": None,
        "beam1_pdgid": None,
        "beam2_pdgid": None,
        "beam1_energy_gev": None,
        "beam2_energy_gev": None,
    }

    if not init_lines:
        return information

    header = init_lines[0].split()

    if len(header) < 10:
        return information

    information["beam1_pdgid"] = int(header[0])
    information["beam2_pdgid"] = int(header[1])
    information["beam1_energy_gev"] = parse_lhe_number(header[2])
    information["beam2_energy_gev"] = parse_lhe_number(header[3])

    process_count = int(header[9])
    process_lines = init_lines[1 : process_count + 1]

    cross_section = 0.0
    squared_error = 0.0
    parsed_processes = 0

    for process_line in process_lines:
        fields = process_line.split()

        if len(fields) < 2:
            continue

        value = parse_lhe_number(fields[0])
        error = parse_lhe_number(fields[1])

        cross_section += value
        squared_error += error * error
        parsed_processes += 1

    if parsed_processes:
        information["cross_section_pb"] = cross_section
        information["cross_section_error_pb"] = math.sqrt(squared_error)

    return information


def parse_lhe_number(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))


def parse_podio_event_count(output: str) -> int:
    match = re.search(
        r"(?m)^\s*events\s+(\d+)\s*$",
        output,
    )

    if match is None:
        raise RuntimeError(
            "The EDM4hep event count could not be read from podio-dump."
        )

    return int(match.group(1))