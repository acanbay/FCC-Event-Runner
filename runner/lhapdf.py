"""LHAPDF discovery and installation for writable user environments."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def inspect_lhapdf(
    lhaid: int | None,
    cache_directory: Path,
    environment: dict[str, str],
) -> dict[str, Any] | None:
    return prepare_lhapdf(
        lhaid=lhaid,
        cache_directory=cache_directory,
        environment=environment,
        install=False,
    )


def prepare_lhapdf(
    lhaid: int | None,
    cache_directory: Path,
    environment: dict[str, str],
    install: bool = True,
) -> dict[str, Any] | None:
    if lhaid is None:
        return None

    cache_directory = cache_directory.expanduser().resolve()

    if install:
        cache_directory.mkdir(parents=True, exist_ok=True)

    search_paths = collect_lhapdf_paths(
        cache_directory,
        environment,
    )

    pdf_information = find_pdf_information(
        lhaid,
        search_paths,
    )

    if pdf_information is None and install:
        update_lhapdf_index(
            cache_directory,
            search_paths,
            environment,
        )

        search_paths = collect_lhapdf_paths(
            cache_directory,
            environment,
        )

        pdf_information = find_pdf_information(
            lhaid,
            search_paths,
        )

    if pdf_information is None:
        return {
            "lhaid": lhaid,
            "name": None,
            "member": None,
            "installed": False,
            "cache_directory": str(cache_directory),
        }

    pdf_name, member = pdf_information
    installed = pdf_is_installed(pdf_name, search_paths)

    if not installed and install:
        install_pdf_set(
            pdf_name,
            cache_directory,
            search_paths,
            environment,
        )

        search_paths = collect_lhapdf_paths(
            cache_directory,
            environment,
        )

        installed = pdf_is_installed(
            pdf_name,
            search_paths,
        )

    if install and not installed:
        raise RuntimeError(
            f"LHAPDF set installation failed: {pdf_name}"
        )

    environment["LHAPDF_DATA_PATH"] = os.pathsep.join(
        str(path) for path in search_paths
    )

    return {
        "lhaid": lhaid,
        "name": pdf_name,
        "member": member,
        "installed": installed,
        "cache_directory": str(cache_directory),
    }


def collect_lhapdf_paths(
    cache_directory: Path,
    environment: dict[str, str],
) -> list[Path]:
    paths = [cache_directory]

    for value in environment.get(
        "LHAPDF_DATA_PATH",
        "",
    ).split(os.pathsep):
        if value:
            paths.append(Path(value))

    lhapdf_config = shutil.which(
        "lhapdf-config",
        path=environment.get("PATH"),
    )

    if lhapdf_config:
        result = subprocess.run(
            [lhapdf_config, "--datadir"],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.strip():
                    paths.append(Path(line.strip()))

    unique_paths: list[Path] = []

    for path in paths:
        if path not in unique_paths:
            unique_paths.append(path)

    return unique_paths


def find_pdf_information(
    lhaid: int,
    search_paths: list[Path],
) -> tuple[str, int] | None:
    entries: dict[int, str] = {}

    for directory in search_paths:
        index_file = directory / "pdfsets.index"

        if not index_file.is_file():
            continue

        for line in index_file.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines():
            fields = line.split()

            if len(fields) >= 2 and fields[0].isdigit():
                entries[int(fields[0])] = fields[1]

    possible_base_ids = [
        base_id
        for base_id in entries
        if base_id <= lhaid
    ]

    if not possible_base_ids:
        return None

    base_id = max(possible_base_ids)

    return entries[base_id], lhaid - base_id


def pdf_is_installed(
    pdf_name: str,
    search_paths: list[Path],
) -> bool:
    return any(
        (directory / pdf_name / f"{pdf_name}.info").is_file()
        for directory in search_paths
    )


def update_lhapdf_index(
    cache_directory: Path,
    search_paths: list[Path],
    environment: dict[str, str],
) -> None:
    lhapdf = require_lhapdf_command(environment)

    command_environment = dict(environment)
    command_environment["LHAPDF_DATA_PATH"] = os.pathsep.join(
        str(path)
        for path in [cache_directory, *search_paths]
    )

    print("\nUpdating the LHAPDF set index...")

    subprocess.run(
        [lhapdf, "update"],
        check=True,
        env=command_environment,
    )


def install_pdf_set(
    pdf_name: str,
    cache_directory: Path,
    search_paths: list[Path],
    environment: dict[str, str],
) -> None:
    lhapdf = require_lhapdf_command(environment)

    command_environment = dict(environment)
    command_environment["LHAPDF_DATA_PATH"] = os.pathsep.join(
        str(path)
        for path in [cache_directory, *search_paths]
    )

    print(f"\nInstalling LHAPDF set: {pdf_name}")

    subprocess.run(
        [lhapdf, "install", pdf_name],
        check=True,
        env=command_environment,
    )


def require_lhapdf_command(
    environment: dict[str, str],
) -> str:
    command = shutil.which(
        "lhapdf",
        path=environment.get("PATH"),
    )

    if command is None:
        raise RuntimeError(
            "The 'lhapdf' command was not found in the Key4hep environment."
        )

    return command