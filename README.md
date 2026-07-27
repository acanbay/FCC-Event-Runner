# FCC Event Runner

FCC Event Runner provides two independent command-line workflows:

```text
fcc-run  : MadGraph5 -> LHE -> Pythia8 -> Delphes -> EDM4hep ROOT
fcc-skim : EDM4hep ROOT -> FCCAnalyses preselections -> flat ROOT
```

The project uses native MadGraph, Pythia and Delphes cards for event
generation and a separate YAML configuration for skimming. It does not require
installation as a Python package.

## Requirements

FCC Event Runner requires a working Key4hep environment. If the required
commands are already available in `PATH`, the active environment is used
without modification.

Otherwise, FCC Event Runner sources the setup file specified by
`FCC_KEY4HEP_SETUP`. When the variable is not set, the default is:

```text
/cvmfs/sw.hsf.org/key4hep/setup.sh
```

The default works on systems that expose the CERN CVMFS repositories. On other
systems, set `FCC_KEY4HEP_SETUP` to the available Key4hep setup file. FCC Event
Runner does not install Key4hep or provide access to external software
repositories.

| Command | Required executables |
|---|---|
| `fcc-run` | `mg5_aMC`, `DelphesPythia8_EDM4HEP`, `podio-dump`, `lhapdf`, `lhapdf-config` |
| `fcc-skim` | `fccanalysis` |

## Event generation

Run the included production without jet matching:

```bash
./bin/fcc-run examples/ttbar/config.yaml
```

Run the included kT-MLM matching example:

```bash
./bin/fcc-run examples/wjets/config.yaml
```

Each production uses:

```text
config.yaml
sample.mg5
sample_pythia.cmd
```

The YAML file only connects the native cards:

```yaml
madgraph_card: sample.mg5
pythia_card: sample_pythia.cmd
delphes_card: ${DELPHES_DIR}/cards/FCC/scenarios/FCChh_II.tcl
edm4hep_card: ${K4SIMDELPHES}/edm4hep_output_config.tcl
```

The MadGraph card owns the process, model, beams, event count, seed, PDF,
matching parameters and output name. The Pythia card owns showering,
hadronization and matching settings. `fcc-run` additionally provides:

- Writable LHAPDF caching and installation of a missing requested set
- Dry-run and PDF-only preparation modes
- Optional interactive confirmation
- Safe replacement of an existing validated output
- Optional retention of LHE and MadGraph work data
- EDM4hep validation, production logs and JSON metadata

See the complete [event-generation guide](docs/event-generation.md) for the
card contract, all command options and output contents.

## Skimming

Apply the included skim configuration:

```bash
./bin/fcc-skim \
  input.root \
  output.root \
  examples/skim/config.yaml
```

The skim YAML defines:

- Jet, electron, muon and missing-momentum collections
- Object transverse-momentum and pseudorapidity requirements
- Central, forward and b-tagged jet definitions
- Multiplicity, missing-momentum and dilepton-mass preselections
- Same-sign or opposite-sign dilepton charge
- Included or vetoed dilepton-mass windows

`fcc-skim` validates the configuration, runs FCCAnalyses with the podio
DataSource and writes a flat ROOT ntuple containing event weight, object
multiplicities and selected-object kinematics. It supports dry-run inspection
and safe replacement of an existing output. FCCAnalyses runs in one thread.

See the complete [skimming guide](docs/skimming.md) for the YAML contract,
preselection syntax, command options and output branches.

## Documentation

| Guide | Contents |
|---|---|
| [Event generation](docs/event-generation.md) | MadGraph and Pythia cards, LHAPDF handling, options, validation and outputs |
| [Skimming](docs/skimming.md) | Object definitions, preselection language, options and flat ROOT output |

## Included examples

| Directory | Purpose |
|---|---|
| [`examples/ttbar`](examples/ttbar) | Event generation without jet matching |
| [`examples/wjets`](examples/wjets) | Event generation with kT-MLM matching |
| [`examples/skim`](examples/skim) | Object definitions and same-sign dilepton preselections |

Example matching scales demonstrate the configuration mechanism and must be
validated for a specific production.

## External execution

FCC Event Runner contains no batch-system or software-mounting logic. An
external wrapper may prepare the software environment and call either command:

```bash
/path/to/FCC-Event-Runner/bin/fcc-run config.yaml
/path/to/FCC-Event-Runner/bin/fcc-skim input.root output.root skim.yaml
```

## Author

Ali Can Canbay
Ankara University
acanbay@ankara.edu.tr

## References

- [FCC Software](https://hep-fcc.github.io/FCCSW/)
- [FCCAnalyses](https://hep-fcc.github.io/FCCAnalyses/)
- [Key4hep](https://key4hep.github.io/key4hep-doc/)
