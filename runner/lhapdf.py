"""Writable LHAPDF cache support."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def prepare_lhapdf(
    lhaid: int | None,
    cache: Path,
    environment: dict[str, str],
    install: bool,
) -> dict[str, Any] | None:
    if lhaid is None:
        return None

    cache = cache.expanduser().resolve()
    if install:
        cache.mkdir(parents=True, exist_ok=True)

    paths = lhapdf_paths(cache, environment)
    pdf = find_pdf(lhaid, paths)

    if pdf is None and install:
        run_lhapdf(["update"], cache, paths, environment)
        paths = lhapdf_paths(cache, environment)
        pdf = find_pdf(lhaid, paths)

    if pdf is None:
        return {
            "lhaid": lhaid,
            "name": None,
            "member": None,
            "installed": False,
        }

    name, member = pdf
    installed = any(
        (path / name / f"{name}.info").is_file()
        for path in paths
    )

    if install and not installed:
        run_lhapdf(["install", name], cache, paths, environment)
        paths = lhapdf_paths(cache, environment)
        installed = any(
            (path / name / f"{name}.info").is_file()
            for path in paths
        )
        if not installed:
            raise RuntimeError(f"LHAPDF installation failed: {name}")

    environment["LHAPDF_DATA_PATH"] = os.pathsep.join(map(str, paths))
    return {
        "lhaid": lhaid,
        "name": name,
        "member": member,
        "installed": installed,
    }


def lhapdf_paths(
    cache: Path,
    environment: dict[str, str],
) -> list[Path]:
    paths = [cache]
    paths.extend(
        Path(value)
        for value in environment.get("LHAPDF_DATA_PATH", "").split(os.pathsep)
        if value
    )

    command = shutil.which("lhapdf-config", path=environment.get("PATH"))
    if command:
        result = subprocess.run(
            [command, "--datadir"],
            env=environment,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            paths.append(Path(result.stdout.strip()))

    return list(dict.fromkeys(paths))


def find_pdf(
    lhaid: int,
    paths: list[Path],
) -> tuple[str, int] | None:
    entries: dict[int, str] = {}
    for path in paths:
        index = path / "pdfsets.index"
        if not index.is_file():
            continue
        for line in index.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[0].isdigit():
                entries[int(fields[0])] = fields[1]

    base_ids = [base_id for base_id in entries if base_id <= lhaid]
    if not base_ids:
        return None

    base_id = max(base_ids)
    return entries[base_id], lhaid - base_id


def run_lhapdf(
    arguments: list[str],
    cache: Path,
    paths: list[Path],
    environment: dict[str, str],
) -> None:
    command = shutil.which("lhapdf", path=environment.get("PATH"))
    if command is None:
        raise RuntimeError("'lhapdf' was not found in the loaded environment.")

    child_environment = dict(environment)
    child_environment["LHAPDF_DATA_PATH"] = os.pathsep.join(
        map(str, [cache, *paths])
    )
    action = "Installing" if arguments[0] == "install" else "Updating"
    print(f"\n{action} LHAPDF data...")
    subprocess.run(
        [command, *arguments],
        check=True,
        env=child_environment,
    )
