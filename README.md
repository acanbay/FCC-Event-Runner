# FCC Event Runner

FCC Event Runner executes:

```text
MadGraph5 -> LHE -> Pythia8 -> Delphes -> EDM4hep ROOT
```

It also provides a separate skim command:

```text
EDM4hep ROOT -> FCCAnalyses preselection -> flat ROOT
```

It uses the software already provided by a loaded Key4hep environment. No
installation or Python package is required.

## Quick start

Run the complete ttbar example:

```bash
./bin/fcc-run examples/ttbar/config.yaml
```

If the Key4hep commands are not already available, `fcc-run` loads
`/cvmfs/sw.hsf.org/key4hep/setup.sh` automatically. CVMFS must be mounted, but
the user does not need to source Key4hep manually.

Run with a persistent writable LHAPDF cache:

```bash
./bin/fcc-run \
  --lhapdf-dir "$HOME/softwares/lhapdf_data" \
  examples/ttbar/config.yaml
```

The runner installs the PDF requested by the MadGraph card when it is missing,
then runs the complete production chain.

## Skimming

Apply object definitions and preselections to an EDM4hep sample:

```bash
./bin/fcc-skim \
  input.root \
  output.root \
  examples/skim/config.yaml
```

`fcc-skim` loads Key4hep automatically when `fccanalysis` is not already
available. CVMFS must already be mounted; the command does not mount software
repositories. The existing `fcc-run` production workflow is not involved.

Inspect and validate a skim configuration without producing an output:

```bash
./bin/fcc-skim \
  --dry-run \
  input.root \
  output.root \
  examples/skim/config.yaml
```

Replace an existing output:

```bash
./bin/fcc-skim \
  --overwrite \
  input.root \
  output.root \
  examples/skim/config.yaml
```

`fcc-skim` runs FCCAnalyses in a single thread for stable podio DataSource
processing.

The output is a compact flat ROOT analysis ntuple, not another EDM4hep file.
It contains selected object kinematics, object multiplicities, missing
transverse momentum, dilepton mass, dilepton charge product and event weight.

### Skim configuration

Object definitions are kept separate from event preselections:

```yaml
objects:
  jet:
    collection: Jet
    pt_min: 30
    abs_eta_max: 6.0
    central_abs_eta_max: 2.5
    forward_abs_eta_min: 2.5
    forward_abs_eta_max: 6.0
    btag:
      collection: Jet_HF_tags
      bit: 0

  electron:
    collection: Electron
    pt_min: 25
    abs_eta_max: 4.0

  muon:
    collection: Muon
    pt_min: 25
    abs_eta_max: 4.0

  MET:
    collection: MissingET

preselections: |
  jet_size >= 2
  bjet_size >= 1
  fjet_size >= 1
  lepton_size == 2
  SS
  MET > 30
  mll > 20
  mll_window 81 101 veto
```

The following multiplicities are available:

```text
jet_size
central_jet_size
bjet_size
fjet_size
electron_size
muon_size
lepton_size
```

Every preselection line is optional. Supported kinematic variables are `MET`
and `mll`. Dilepton charge can be selected with `SS` or `OS`.

An invariant-mass window has the form:

```text
mll_window LOW HIGH veto
mll_window LOW HIGH include
```

`SS`, `OS`, `mll` and `mll_window` require `lepton_size == 2`, preventing an
ambiguous dilepton choice.

The heavy-flavour tag is read from the configured `ParticleID` collection.
For the current `FCChh_II.tcl` card, b-tag bits 0, 1 and 2 correspond to the
loose, medium and tight working points. The desired bit remains an explicit
analysis choice in the YAML file. B-tagged jets are always restricted to the
configured central-jet acceptance.

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
fccanalysis
```

## Batch systems

The runner contains no batch-system or software-mounting logic. An external
job wrapper prepares the environment and calls:

```bash
/path/to/FCC-Event-Runner/bin/fcc-run config.yaml
/path/to/FCC-Event-Runner/bin/fcc-skim input.root output.root skim.yaml
```

## References

- [FCC Software](https://hep-fcc.github.io/FCCSW/)
- [FCCAnalyses](https://hep-fcc.github.io/FCCAnalyses/)
- [Key4hep](https://key4hep.github.io/key4hep-doc/)
