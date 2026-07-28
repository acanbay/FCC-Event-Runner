"""Delphes TreeWriter discovery and EDM4hep output-card generation."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path


OUTPUT_GROUP_BY_CLASS = {
    "GenParticle": "GenParticleCollections",
    "Track": "ReconstructedParticleCollections",
    "Tower": "ReconstructedParticleCollections",
    "ParticleFlowCandidate": "ReconstructedParticleCollections",
    "Jet": "JetCollections",
    "Muon": "MuonCollections",
    "Electron": "ElectronCollections",
    "Photon": "PhotonCollections",
    "MissingET": "MissingETCollections",
    "ScalarHT": "ScalarHTCollections",
}
RECONSTRUCTED_CLASSES = {"Track", "Tower", "ParticleFlowCandidate"}
SUBSET_CLASSES = {"Muon", "Electron", "Photon"}
EMPTY_SELECTION = "__FCC_EVENT_RUNNER_EMPTY__"


@dataclass(frozen=True)
class DelphesBranch:
    input_array: str
    name: str
    branch_class: str


@dataclass(frozen=True)
class OutputSelection:
    available: tuple[DelphesBranch, ...]
    selected: tuple[DelphesBranch, ...]
    card_text: str
    warnings: tuple[str, ...]


def parse_treewriter(card: Path) -> tuple[DelphesBranch, ...]:
    branches: list[DelphesBranch] = []
    inside_treewriter = False
    depth = 0

    for line_number, raw_line in enumerate(
        card.read_text(encoding="utf-8", errors="replace").splitlines(),
        start=1,
    ):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        if not inside_treewriter:
            try:
                fields = shlex.split(line)
            except ValueError:
                fields = []
            if (
                len(fields) >= 3
                and fields[:2] == ["module", "TreeWriter"]
            ):
                inside_treewriter = True
                depth = line.count("{") - line.count("}")
            continue

        depth += line.count("{") - line.count("}")
        command = line.replace("}", " ").strip()
        if command:
            try:
                fields = shlex.split(command)
            except ValueError as error:
                raise RuntimeError(
                    f"Invalid TreeWriter syntax in {card}:{line_number}."
                ) from error
            if fields[:2] == ["add", "Branch"]:
                if len(fields) != 5:
                    raise RuntimeError(
                        "Expected 'add Branch InputArray BranchName "
                        f"BranchClass' in {card}:{line_number}."
                    )
                branches.append(
                    DelphesBranch(
                        input_array=fields[2],
                        name=fields[3],
                        branch_class=fields[4],
                    )
                )

        if depth <= 0:
            inside_treewriter = False

    if not branches:
        raise RuntimeError(
            f"No TreeWriter branch definitions were found in {card}."
        )

    names = [branch.name for branch in branches]
    duplicates = sorted(
        name for name in set(names) if names.count(name) > 1
    )
    if duplicates:
        raise RuntimeError(
            "Duplicate TreeWriter BranchName value(s): "
            + ", ".join(duplicates)
        )
    return tuple(branches)


def create_output_selection(
    branches: tuple[DelphesBranch, ...],
    requested_names: list[str],
) -> OutputSelection:
    by_name = {branch.name: branch for branch in branches}
    missing = [name for name in requested_names if name not in by_name]
    if missing:
        available = ", ".join(
            f"{branch.name} ({branch.branch_class})"
            for branch in branches
        )
        raise RuntimeError(
            "Unknown Delphes output collection(s): "
            + ", ".join(missing)
            + f"\nAvailable TreeWriter branches: {available}"
        )

    selected = tuple(by_name[name] for name in requested_names)
    unsupported = [
        branch
        for branch in selected
        if branch.branch_class not in OUTPUT_GROUP_BY_CLASS
    ]
    if unsupported:
        values = ", ".join(
            f"{branch.name} ({branch.branch_class})"
            for branch in unsupported
        )
        raise RuntimeError(
            "k4SimDelphes cannot convert the selected branch class(es): "
            + values
        )

    selected_classes = {branch.branch_class for branch in selected}
    subset_branches = [
        branch.name
        for branch in selected
        if branch.branch_class in SUBSET_CLASSES
    ]
    if subset_branches and not selected_classes.intersection(
        RECONSTRUCTED_CLASSES
    ):
        raise RuntimeError(
            "Electron, Muon and Photon branches are EDM4hep subset "
            "collections and require at least one selected Track, Tower or "
            "ParticleFlowCandidate branch. Affected selection: "
            + ", ".join(subset_branches)
        )

    warnings: list[str] = []
    if "Jet" in selected_classes and not selected_classes.intersection(
        RECONSTRUCTED_CLASSES
    ):
        warnings.append(
            "Jet collections will be written without persisted constituents."
        )

    return OutputSelection(
        available=branches,
        selected=selected,
        card_text=render_output_card(selected),
        warnings=tuple(warnings),
    )


def render_output_card(branches: tuple[DelphesBranch, ...]) -> str:
    groups: dict[str, list[str]] = {
        group: []
        for group in dict.fromkeys(OUTPUT_GROUP_BY_CLASS.values())
    }
    for branch in branches:
        groups[OUTPUT_GROUP_BY_CLASS[branch.branch_class]].append(branch.name)

    lines = [
        "# Generated by FCC Event Runner.",
        "module EDM4HepOutput EDM4HepOutput {",
    ]
    for group, names in groups.items():
        values = names
        if not values and group in {
            "GenParticleCollections",
            "ReconstructedParticleCollections",
        }:
            values = [EMPTY_SELECTION]
        for name in values:
            lines.append(f"  add {group} {name}")

    lines.extend(
        [
            "",
            "  set RecoParticleCollectionName ReconstructedParticles",
            "  set RecoMCParticleLinkCollectionName RecoMCLink",
            "}",
        ]
    )
    return "\n".join(lines) + "\n"
