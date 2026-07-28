# FCC Event Runner

FCC Event Runner provides two independent command-line workflows:

```text
fcc-run  : MadGraph5 -> LHE -> Pythia8 -> Delphes -> EDM4hep ROOT
fcc-skim : EDM4hep ROOT -> FCCAnalyses preselections -> flat ROOT
```

The project uses native MadGraph, Pythia and Delphes cards and does not require
installation as a Python package.

## Requirements

A working Key4hep environment is required. An active environment is used
directly. Otherwise, FCC Event Runner loads the setup file specified by
`FCC_KEY4HEP_SETUP`, or `/cvmfs/sw.hsf.org/key4hep/setup.sh` by default.

| Command | Required executables |
|---|---|
| `fcc-run` | `mg5_aMC`, `DelphesPythia8_EDM4HEP`, `podio-dump`, `lhapdf`, `lhapdf-config` |
| `fcc-skim` | `fccanalysis` |

## Quick start

Run the included event-generation example:

```bash
./bin/fcc-run examples/ttbar/config.yaml
```

Its single production YAML connects the required cards:

```yaml
madgraph_card: ttbar.mg5
pythia_card: ttbar_pythia.cmd
delphes_card: ${DELPHES_DIR}/cards/FCC/scenarios/FCChh_II.tcl
```

Without additional settings, the standard k4SimDelphes EDM4hep output
configuration is used. The same YAML may optionally select another output
card or a reduced set of Delphes `TreeWriter` collections. Collection
selection omits unused objects from the EDM4hep ROOT file to reduce storage
requirements without changing the Delphes detector simulation. See the
[event-generation guide](docs/event-generation.md) for the complete
configuration and command options.

Run the included skim example:

```bash
./bin/fcc-skim \
  input.root \
  output.root \
  examples/skim/config.yaml
```

See the [skimming guide](docs/skimming.md) for object definitions,
preselection syntax and output branches.

## Features

`fcc-run` provides writable LHAPDF caching, dry-run and preparation modes,
optional LHE retention, safe output replacement, dynamic EDM4hep collection
selection, output validation, logs and JSON metadata.

`fcc-skim` provides configurable physics-object definitions, multiplicity and
kinematic preselections, dilepton charge and mass selections, safe output
replacement and flat ROOT output.

## Documentation

| Guide | Contents |
|---|---|
| [Event generation](docs/event-generation.md) | Input cards, matching, LHAPDF, EDM4hep output control, options and metadata |
| [Skimming](docs/skimming.md) | Object definitions, preselection language, options and flat ROOT output |

## Included examples

| Directory | Purpose |
|---|---|
| [`examples/ttbar`](examples/ttbar) | Event generation without jet matching |
| [`examples/wjets`](examples/wjets) | Event generation with kT-MLM matching |
| [`examples/ttbar-output-selection`](examples/ttbar-output-selection) | `ttbar` generation with selected EDM4hep output collections |
| [`examples/skim`](examples/skim) | Same-sign dilepton preselection |

Example matching scales demonstrate the configuration mechanism and must be
validated for a specific production.

## External execution

Batch-system and software-mounting logic remains outside this project. An
external wrapper may prepare the environment and invoke either executable.

## References

- [FCC Software](https://hep-fcc.github.io/FCCSW/)
- [FCCAnalyses](https://hep-fcc.github.io/FCCAnalyses/)
- [Key4hep](https://key4hep.github.io/key4hep-doc/)
- [k4SimDelphes output configuration](https://github.com/key4hep/k4SimDelphes/blob/main/doc/output_config.md)
- [Delphes TreeWriter](https://delphes.github.io/workbook/modules/)
