"""Input parsers used by FCC Event Runner."""

from __future__ import annotations

import math
import re
import shlex
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as error:
    raise RuntimeError("PyYAML is not available in the loaded environment.") from error


REQUIRED_CONFIG_FIELDS = (
    "madgraph_card",
    "pythia_card",
    "delphes_card",
    "edm4hep_card",
)


def load_manifest(path: Path) -> dict[str, str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("The YAML root must be a mapping.")

    missing = [field for field in REQUIRED_CONFIG_FIELDS if field not in data]
    if missing:
        raise RuntimeError(f"Missing YAML field(s): {', '.join(missing)}")

    return {field: str(data[field]) for field in REQUIRED_CONFIG_FIELDS}


def parse_madgraph_card(path: Path) -> dict[str, Any]:
    output: str | None = None
    settings: dict[str, str] = {}

    for raw_line in path.read_text(
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

        if fields[0].lower() == "output" and len(fields) > 1:
            output = fields[1]
        elif fields[0].lower() == "set" and len(fields) > 2:
            settings[fields[1].lower()] = fields[2]

    if output is None:
        raise RuntimeError(f"No 'output <directory>' command in {path}.")

    output_path = Path(output)
    if (
        output_path.is_absolute()
        or ".." in output_path.parts
        or output_path in {Path("."), Path("")}
    ):
        raise RuntimeError("MadGraph output must be a safe relative path.")

    def integer(name: str, default: int | None = None) -> int | None:
        try:
            return int(settings[name])
        except (KeyError, ValueError):
            return default

    def number(name: str) -> float | None:
        try:
            return float(
                settings[name].replace("D", "E").replace("d", "e")
            )
        except (KeyError, ValueError):
            return None

    return {
        "output_directory": output,
        "sample_name": output_path.name,
        "nevents": integer("nevents"),
        "iseed": integer("iseed"),
        "ebeam1": number("ebeam1"),
        "ebeam2": number("ebeam2"),
        "lhaid": integer("lhaid"),
        "ickkw": integer("ickkw", 0),
        "xqcut": number("xqcut"),
    }


def matching_description(mg: dict[str, Any]) -> str:
    if mg["ickkw"] == 0:
        return "Disabled"
    if mg["ickkw"] == 1:
        return (
            f"MLM (xqcut = {mg['xqcut']:g} GeV)"
            if mg["xqcut"] is not None
            else "MLM"
        )
    if mg["ickkw"] == 3:
        return "FxFx"
    return f"Enabled (ickkw = {mg['ickkw']})"


def render_template(path: Path, replacements: dict[str, Any]) -> str:
    content = path.read_text(encoding="utf-8")
    for name, value in replacements.items():
        content = content.replace(f"@{name}@", str(value))

    unresolved = sorted(set(re.findall(r"@([A-Z][A-Z0-9_]*)@", content)))
    if unresolved:
        fields = ", ".join(f"@{name}@" for name in unresolved)
        raise RuntimeError(f"Unresolved field(s) in {path}: {fields}")
    return content


def parse_lhe(path: Path) -> dict[str, Any]:
    events = 0
    init_lines: list[str] = []
    inside_init = False

    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for raw_line in stream:
            line = raw_line.strip()
            if line.startswith("<event"):
                events += 1
            elif line.startswith("<init"):
                inside_init = True
            elif line.startswith("</init"):
                inside_init = False
            elif inside_init and line and not line.startswith("#"):
                init_lines.append(line)

    result = {
        "events": events,
        "cross_section_pb": None,
        "cross_section_error_pb": None,
    }
    if not init_lines:
        return result

    header = init_lines[0].split()
    if len(header) < 10:
        return result

    process_count = int(header[9])
    cross_section = 0.0
    error_squared = 0.0
    parsed = 0

    for line in init_lines[1 : process_count + 1]:
        fields = line.split()
        if len(fields) < 2:
            continue
        value = float(fields[0].replace("D", "E").replace("d", "e"))
        error = float(fields[1].replace("D", "E").replace("d", "e"))
        cross_section += value
        error_squared += error * error
        parsed += 1

    if parsed:
        result["cross_section_pb"] = cross_section
        result["cross_section_error_pb"] = math.sqrt(error_squared)
    return result


def parse_pythia_cross_section(path: Path) -> dict[str, float | None]:
    """Read the post-shower cross section reported by Pythia8."""
    pattern = re.compile(
        r"Pythia8 Cross-section\s*\(.*?\):\s*"
        r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?)\s*"
        r"\+/-\s*"
        r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?)\s*pb"
    )
    match = pattern.search(path.read_text(encoding="utf-8", errors="replace"))
    if match is None:
        return {
            "cross_section_pb": None,
            "cross_section_error_pb": None,
        }
    return {
        "cross_section_pb": float(match.group(1)),
        "cross_section_error_pb": float(match.group(2)),
    }


def parse_podio_event_count(output: str) -> int:
    match = re.search(r"(?m)^\s*events\s+(\d+)\s*$", output)
    if match is None:
        raise RuntimeError("Could not read the event count from podio-dump.")
    return int(match.group(1))
