# Event Generation

`fcc-run` executes:

```text
MadGraph5 -> LHE -> Pythia8 -> Delphes -> EDM4hep ROOT
```

Run a production:

```bash
./bin/fcc-run path/to/config.yaml
```

## Production files

Each production requires one YAML manifest, one MadGraph card and one Pythia
card:

```text
sample/
├── config.yaml
├── sample.mg5
└── sample_pythia.cmd
```

The YAML manifest connects these cards to the detector and EDM4hep output
configurations:

```yaml
madgraph_card: sample.mg5
pythia_card: sample_pythia.cmd
delphes_card: ${DELPHES_DIR}/cards/FCC/scenarios/FCChh_II.tcl
edm4hep_card: ${K4SIMDELPHES}/edm4hep_output_config.tcl
```

Relative paths are resolved from the YAML directory. Environment variables and
home-directory references are expanded.

## MadGraph card

The native MadGraph card remains the single source for:

- Model and process definitions
- Decay syntax and generation cuts
- Event count and random seed
- Beam types and energies
- PDF choice
- Matching or merging parameters
- Masses, couplings and other model parameters
- MadGraph output directory

The output directory must be a safe relative path:

```text
output work/sample_name
```

Its basename defines the sample name. The example above produces
`sample_name.root` and `sample_name.metadata.json`.

MadGraph showering, detector simulation and analysis are disabled because
Pythia8 and Delphes are executed explicitly by `fcc-run`.

## Pythia card

The Pythia card may use these runtime fields:

```text
@LHE_FILE@     generated LHE path
@LHE_EVENTS@   number of events found in the LHE file
@PYTHIA_SEED@  seed derived from the MadGraph seed
```

The card also owns all showering, hadronization and matching settings. An
unresolved `@FIELD@` causes the production to stop before Pythia8 is started.

## LHAPDF handling

When the MadGraph card requests an LHAPDF ID, `fcc-run` locates the
corresponding set and installs it when missing. The default writable cache is:

```text
~/.local/share/fcc-event-runner/lhapdf
```

Use a persistent alternative:

```bash
./bin/fcc-run \
  --lhapdf-dir /path/to/lhapdf_data \
  path/to/config.yaml
```

## Command options

| Option | Behaviour |
|---|---|
| `--dry-run` | Validate cards and print the resolved production without writing files. |
| `--prepare` | Install a missing PDF and stop before event generation. |
| `--confirm` | Wait for Enter before starting an interactive production. |
| `--overwrite` | Replace an existing validated output only after the new output succeeds. |
| `--keep-lhe` | Save the generated LHE file as `outputs/<sample>.lhe.gz`. |
| `--keep-work` | Preserve the successful MadGraph output directory. |
| `--lhapdf-dir PATH` | Select the writable LHAPDF cache. |

`--dry-run` and `--prepare` are mutually exclusive.

## Outputs

A successful production writes:

```text
outputs/<sample>.root
outputs/<sample>.metadata.json
logs/<sample>/<UTC timestamp>/
```

The EDM4hep output is validated with `podio-dump` and must contain at least one
event. Its event count may differ from the requested MadGraph count after
matching or filtering. The file is moved into place only after validation.

The metadata JSON records event counts, cross section and uncertainty, beam
energies, LHAPDF ID, matching mode, seeds, cards and executable paths. Logs
contain the MadGraph, Pythia/Delphes and validation output together with the
resolved run card, parameter card and banner.

Successful MadGraph work directories are removed unless `--keep-work` is used.
Failed MadGraph directories are preserved for diagnosis.

## Examples

- [`examples/ttbar`](../examples/ttbar) demonstrates production without jet
  matching.
- [`examples/wjets`](../examples/wjets) demonstrates kT-MLM matching.

The matching scales in the W+jets example demonstrate the configuration
mechanism and must be validated for a specific production.
