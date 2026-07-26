# FCC Event Runner

FCC Event Runner executes:

```text
MadGraph5 -> LHE -> Pythia8 -> Delphes -> EDM4hep ROOT
```

It uses the software already provided by a loaded Key4hep environment. No
installation or Python package is required.

## Quick start

Load Key4hep:

```bash
source /cvmfs/sw.hsf.org/key4hep/setup.sh -r 2026-04-08
chmod +x bin/fcc-run
```

Run the complete ttbar example:

```bash
./bin/fcc-run examples/ttbar/config.yaml
```

Run with a persistent writable LHAPDF cache:

```bash
./bin/fcc-run \
  --lhapdf-dir "$HOME/softwares/lhapdf_data" \
  examples/ttbar/config.yaml
```

The runner installs the PDF requested by the MadGraph card when it is missing,
then runs the complete production chain.

## Production files

Each production uses:

```text
config.yaml
sample.mg5
sample_pythia.cmd
```

The YAML file only connects the native cards:

```yaml
madgraph_card: ttbar.mg5
pythia_card: ttbar_pythia.cmd
delphes_card: ${DELPHES_DIR}/cards/FCC/scenarios/FCChh_II.tcl
edm4hep_card: ${K4SIMDELPHES}/edm4hep_output_config.tcl
```

Event count, beams, PDF, seed, model, process, cuts, matching settings and the
output name remain in the MadGraph card.

The basename of the MadGraph output directory becomes the sample name:

```text
output work/ttbar
```

produces:

```text
outputs/ttbar.root
outputs/ttbar.metadata.json
```

The Pythia card may use:

```text
@LHE_FILE@
@LHE_EVENTS@
@PYTHIA_SEED@
```

These fields are filled automatically from the generated sample.

## Useful options

Inspect the resolved production:

```bash
./bin/fcc-run --dry-run examples/ttbar/config.yaml
```

Install a missing PDF without generating events:

```bash
./bin/fcc-run --prepare examples/ttbar/config.yaml
```

Require confirmation:

```bash
./bin/fcc-run --confirm examples/ttbar/config.yaml
```

Replace an existing output only after the new output validates:

```bash
./bin/fcc-run --overwrite examples/ttbar/config.yaml
```

Keep optional intermediate data:

```bash
./bin/fcc-run --keep-lhe --keep-work examples/ttbar/config.yaml
```

## Outputs

Every successful production contains:

- An EDM4hep ROOT file
- JSON metadata with event counts, cross section, beam energies, PDF, seeds,
  matching mode, cards and executable paths
- MadGraph, Pythia/Delphes and validation logs
- The generated MadGraph run card, parameter card and banner

Failed MadGraph directories are preserved. Successful MadGraph directories are
removed unless `--keep-work` is used. The generated LHE file is only retained
when `--keep-lhe` is used.

The EDM4hep event count must be positive but is not required to equal the
requested MadGraph count. Matching or filtering may reduce it.

## Examples

`examples/ttbar` demonstrates production without jet matching.

`examples/wjets` demonstrates kT-MLM matching with matrix-element samples
containing zero, one and two light partons. Its matching-scale values are
examples and must be validated before a large production.

## Required commands

The loaded environment must provide:

```text
mg5_aMC
DelphesPythia8_EDM4HEP
podio-dump
lhapdf
lhapdf-config
```

## Batch systems

The runner contains no Slurm, TRUBA, HTCondor or CVMFSexec logic. A batch job
loads its environment and calls:

```bash
/path/to/FCC-Event-Runner/bin/fcc-run config.yaml
```

## Author

Ali Can Canbay  
Ankara University  
acanbay@ankara.edu.tr

## References

- [FCC Software](https://hep-fcc.github.io/FCCSW/)
- [Key4hep](https://key4hep.github.io/key4hep-doc/)