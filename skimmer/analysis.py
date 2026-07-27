# Author: Ali Can Canbay <acanbay@ankara.edu.tr>

"""Internal FCCAnalyses workflow used by the fcc-skim command."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config


KINEMATIC_OUTPUTS = ("pt", "eta", "phi", "mass")
PARTICLE_PREFIXES = (
    "jet",
    "central_jet",
    "bjet",
    "fjet",
    "electron",
    "muon",
    "lepton",
)


class Analysis:
    """Build a flat analysis ntuple after configurable preselections."""

    def __init__(self, cmdline_args):
        parser = ArgumentParser(description="FCC Event Runner skim arguments")
        parser.add_argument("--config", required=True)
        arguments, _ = parser.parse_known_args(cmdline_args["remaining"])

        self.config = load_config(Path(arguments.config))
        self.process_list = {}
        self.n_threads = 1
        self.use_data_source = True
        self.include_paths = ["helpers.h"]

    def analyzers(self, dframe):
        jet = self.config.jet
        electron = self.config.electron
        muon = self.config.muon
        met = self.config.met

        result = (
            dframe
            .Define(
                "selected_jets",
                "FCCEventRunnerSkim::select("
                f"{jet.collection}, {jet.pt_min}, 0., {jet.abs_eta_max})",
            )
            .Define(
                "selected_central_jets",
                "FCCEventRunnerSkim::select("
                f"{jet.collection}, {jet.pt_min}, 0., "
                f"{jet.central_abs_eta_max})",
            )
            .Define(
                "selected_forward_jets",
                "FCCEventRunnerSkim::select("
                f"{jet.collection}, {jet.pt_min}, "
                f"{jet.forward_abs_eta_min}, {jet.forward_abs_eta_max})",
            )
            .Define(
                "selected_bjets",
                "FCCEventRunnerSkim::selectBJets("
                f"{jet.collection}, {jet.btag.collection}, {jet.btag.bit}, "
                f"{jet.pt_min}, {jet.central_abs_eta_max})",
            )
            .Define(
                "selected_electrons",
                "FCCEventRunnerSkim::select("
                f"{electron.collection}, {electron.pt_min}, 0., "
                f"{electron.abs_eta_max})",
            )
            .Define(
                "selected_muons",
                "FCCEventRunnerSkim::select("
                f"{muon.collection}, {muon.pt_min}, 0., "
                f"{muon.abs_eta_max})",
            )
            .Define(
                "selected_leptons",
                "FCCEventRunnerSkim::merge("
                "selected_electrons, selected_muons)",
            )
            .Define("jet_size", "int(selected_jets.size())")
            .Define(
                "central_jet_size",
                "int(selected_central_jets.size())",
            )
            .Define("bjet_size", "int(selected_bjets.size())")
            .Define("fjet_size", "int(selected_forward_jets.size())")
            .Define("electron_size", "int(selected_electrons.size())")
            .Define("muon_size", "int(selected_muons.size())")
            .Define("lepton_size", "int(selected_leptons.size())")
            .Define("MET", f"FCCEventRunnerSkim::met({met.collection})")
            .Define("mll", "FCCEventRunnerSkim::mll(selected_leptons)")
            .Define(
                "dilepton_charge_product",
                "FCCEventRunnerSkim::chargeProduct(selected_leptons)",
            )
            .Define(
                "event_weight",
                "FCCEventRunnerSkim::eventWeight(EventHeader)",
            )
        )

        collections = {
            "jet": "selected_jets",
            "central_jet": "selected_central_jets",
            "bjet": "selected_bjets",
            "fjet": "selected_forward_jets",
            "electron": "selected_electrons",
            "muon": "selected_muons",
            "lepton": "selected_leptons",
        }
        for prefix, collection in collections.items():
            for variable in KINEMATIC_OUTPUTS:
                result = result.Define(
                    f"{prefix}_{variable}",
                    f"FCCEventRunnerSkim::{variable}({collection})",
                )
        result = result.Define(
            "electron_charge",
            "FCCEventRunnerSkim::charge(selected_electrons)",
        )
        result = result.Define(
            "muon_charge",
            "FCCEventRunnerSkim::charge(selected_muons)",
        )
        result = result.Define(
            "lepton_charge",
            "FCCEventRunnerSkim::charge(selected_leptons)",
        )

        for selection in self.config.selections:
            result = result.Filter(selection.expression(), selection.source)
        return result

    def output(self):
        branches = [
            "event_weight",
            "jet_size",
            "central_jet_size",
            "bjet_size",
            "fjet_size",
            "electron_size",
            "muon_size",
            "lepton_size",
            "MET",
            "mll",
            "dilepton_charge_product",
        ]
        for prefix in PARTICLE_PREFIXES:
            branches.extend(
                f"{prefix}_{variable}" for variable in KINEMATIC_OUTPUTS
            )
        branches.extend(
            ["electron_charge", "muon_charge", "lepton_charge"]
        )
        return branches
