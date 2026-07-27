# Author: Ali Can Canbay <acanbay@ankara.edu.tr>

"""Validation and parsing for FCC Event Runner skim configurations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COMPARISON = re.compile(
    r"^(jet_size|central_jet_size|bjet_size|fjet_size|"
    r"electron_size|muon_size|lepton_size|MET|mll)"
    r"\s*(>=|<=|==|>|<)\s*(-?(?:\d+(?:\.\d*)?|\.\d+))$"
)
MLL_WINDOW = re.compile(
    r"^mll_window\s+"
    r"(-?(?:\d+(?:\.\d*)?|\.\d+))\s+"
    r"(-?(?:\d+(?:\.\d*)?|\.\d+))\s+"
    r"(veto|include)$",
    re.IGNORECASE,
)
COUNT_VARIABLES = {
    "jet_size",
    "central_jet_size",
    "bjet_size",
    "fjet_size",
    "electron_size",
    "muon_size",
    "lepton_size",
}


@dataclass(frozen=True)
class ParticleConfig:
    collection: str
    pt_min: float
    abs_eta_max: float


@dataclass(frozen=True)
class BTagConfig:
    collection: str
    bit: int


@dataclass(frozen=True)
class JetConfig(ParticleConfig):
    central_abs_eta_max: float
    forward_abs_eta_min: float
    forward_abs_eta_max: float
    btag: BTagConfig


@dataclass(frozen=True)
class MetConfig:
    collection: str


@dataclass(frozen=True)
class Selection:
    kind: str
    source: str
    variable: str | None = None
    operator: str | None = None
    value: float | None = None
    low: float | None = None
    high: float | None = None
    mode: str | None = None

    def expression(self) -> str:
        if self.kind == "comparison":
            return f"{self.variable} {self.operator} {self.value:g}"
        if self.kind == "charge":
            operator = ">" if self.mode == "SS" else "<"
            return f"dilepton_charge_product {operator} 0"
        if self.kind == "mll_window":
            if self.mode == "include":
                return f"mll >= {self.low:g} && mll <= {self.high:g}"
            return f"mll < {self.low:g} || mll > {self.high:g}"
        raise RuntimeError(f"Unsupported selection kind: {self.kind}")


@dataclass(frozen=True)
class SkimConfig:
    path: Path
    jet: JetConfig
    electron: ParticleConfig
    muon: ParticleConfig
    met: MetConfig
    selections: tuple[Selection, ...]


def _mapping(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a YAML mapping.")
    return value


def _identifier(value, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"{label} must be a valid collection name.")
    return value


def _number(mapping: dict, key: str, label: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}.{key} must be a number.")
    return float(value)


def _particle_config(objects: dict, name: str) -> ParticleConfig:
    values = _mapping(objects.get(name), f"objects.{name}")
    pt_min = _number(values, "pt_min", f"objects.{name}")
    abs_eta_max = _number(values, "abs_eta_max", f"objects.{name}")
    if pt_min < 0 or abs_eta_max <= 0:
        raise ValueError(
            f"objects.{name} requires pt_min >= 0 and abs_eta_max > 0."
        )
    return ParticleConfig(
        collection=_identifier(
            values.get("collection"),
            f"objects.{name}.collection",
        ),
        pt_min=pt_min,
        abs_eta_max=abs_eta_max,
    )


def _jet_config(objects: dict) -> JetConfig:
    values = _mapping(objects.get("jet"), "objects.jet")
    base = _particle_config(objects, "jet")
    central = _number(values, "central_abs_eta_max", "objects.jet")
    forward_min = _number(values, "forward_abs_eta_min", "objects.jet")
    forward_max = _number(values, "forward_abs_eta_max", "objects.jet")
    if not 0 < central <= forward_min < forward_max <= base.abs_eta_max:
        raise ValueError(
            "Jet eta limits must satisfy 0 < central_abs_eta_max <= "
            "forward_abs_eta_min < forward_abs_eta_max <= abs_eta_max."
        )

    btag_values = _mapping(values.get("btag"), "objects.jet.btag")
    bit = btag_values.get("bit")
    if isinstance(bit, bool) or not isinstance(bit, int) or bit < 0 or bit > 31:
        raise ValueError("objects.jet.btag.bit must be an integer from 0 to 31.")

    return JetConfig(
        collection=base.collection,
        pt_min=base.pt_min,
        abs_eta_max=base.abs_eta_max,
        central_abs_eta_max=central,
        forward_abs_eta_min=forward_min,
        forward_abs_eta_max=forward_max,
        btag=BTagConfig(
            collection=_identifier(
                btag_values.get("collection"),
                "objects.jet.btag.collection",
            ),
            bit=bit,
        ),
    )


def _parse_selections(value) -> tuple[Selection, ...]:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("preselections must be a non-empty YAML block string.")

    selections = []
    lepton_pair_required = False
    unique_lepton_pair = False

    for line_number, raw_line in enumerate(value.splitlines(), start=1):
        source = raw_line.split("#", 1)[0].strip()
        if not source:
            continue

        comparison = COMPARISON.fullmatch(source)
        if comparison:
            variable, operator, raw_value = comparison.groups()
            number = float(raw_value)
            if variable in COUNT_VARIABLES:
                if not number.is_integer() or number < 0:
                    raise ValueError(
                        f"Preselection line {line_number}: {variable} "
                        "requires a non-negative integer."
                    )
                if variable == "lepton_size" and operator == "==" and number == 2:
                    unique_lepton_pair = True
            if variable in {"MET", "mll"} and number < 0:
                raise ValueError(
                    f"Preselection line {line_number}: {variable} "
                    "threshold cannot be negative."
                )
            if variable == "mll":
                lepton_pair_required = True
            selections.append(
                Selection(
                    kind="comparison",
                    source=source,
                    variable=variable,
                    operator=operator,
                    value=number,
                )
            )
            continue

        if source.upper() in {"SS", "OS"}:
            lepton_pair_required = True
            selections.append(
                Selection(
                    kind="charge",
                    source=source.upper(),
                    mode=source.upper(),
                )
            )
            continue

        window = MLL_WINDOW.fullmatch(source)
        if window:
            low, high, mode = window.groups()
            low_value = float(low)
            high_value = float(high)
            if low_value < 0 or high_value <= low_value:
                raise ValueError(
                    f"Preselection line {line_number}: mll_window requires "
                    "0 <= LOW < HIGH."
                )
            lepton_pair_required = True
            selections.append(
                Selection(
                    kind="mll_window",
                    source=source,
                    low=low_value,
                    high=high_value,
                    mode=mode.lower(),
                )
            )
            continue

        raise ValueError(
            f"Unsupported preselection on line {line_number}: {source}"
        )

    if not selections:
        raise ValueError("preselections does not contain any active line.")
    if lepton_pair_required and not unique_lepton_pair:
        raise ValueError(
            "SS, OS, mll and mll_window require 'lepton_size == 2'."
        )
    return tuple(selections)


def load_config(path: Path) -> SkimConfig:
    if not path.is_file():
        raise ValueError(f"Skim configuration was not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid YAML in {path}: {error}") from error

    root = _mapping(data, "configuration")
    objects = _mapping(root.get("objects"), "objects")
    met_values = _mapping(objects.get("MET"), "objects.MET")

    return SkimConfig(
        path=path.resolve(),
        jet=_jet_config(objects),
        electron=_particle_config(objects, "electron"),
        muon=_particle_config(objects, "muon"),
        met=MetConfig(
            collection=_identifier(
                met_values.get("collection"),
                "objects.MET.collection",
            )
        ),
        selections=_parse_selections(root.get("preselections")),
    )
