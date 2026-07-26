# FCC Event Runner

FCC Event Runner is a lightweight workflow for private FCC event production
with the Key4hep software stack.

It runs:

```text
MadGraph5_aMC@NLO -> LHE -> Pythia8 -> Delphes -> EDM4hep ROOT
```

Physics settings are not duplicated in the runner configuration. They remain
in the MadGraph, Pythia and Delphes cards.

## Quick start

Load a Key4hep environment:

```bash
source /cvmfs/sw.hsf.org/key4hep/setup.sh -r 2026-04-08
```

Make the launcher executable once:

```bash
chmod +x bin/fcc-run
```

Run the complete ttbar example:

```bash
./bin/fcc-run examples/ttbar/config.yaml
```

Run the complete W+jets example:

```bash
./bin/fcc-run examples/wjets/config.yaml
```

The normal command performs the entire workflow. It reads `lhaid` from the
MadGraph card, installs a missing PDF set when necessary, runs event
generation and produces the validated EDM4hep output.

For the ttbar example, the final files are written to:

```text
examples/ttbar/outputs/ttbar.root
examples/ttbar/outputs/ttbar.metadata.json
```

## Required environment

The following commands must be provided by the loaded Key4hep environment:

```text
mg5_aMC
DelphesPythia8_EDM4HEP
podio-dump
lhapdf
lhapdf-config
```

The Key4hep Python environment must also provide a YAML reader. No separate
Python package, virtual environment or FCC Event Runner installation is
required.

## Production configuration

The YAML file only connects the production cards:

```yaml
madgraph_card: ttbar.mg5
pythia_card: ttbar_pythia.cmd
delphes_card: ${DELPHES_DIR}/cards/FCC/scenarios/FCChh_II.tcl
edm4hep_card: ${K4SIMDELPHES}/edm4hep_output_config.tcl
```

Paths are resolved relative to the YAML file. Environment variables such as
`DELPHES_DIR` and `K4SIMDELPHES` are supplied by Key4hep.

The YAML file does not contain:

- Event count
- Beam energies
- LHAPDF ID
- Model parameters
- Generation cuts
- Random seed
- Matching parameters
- Output sample name

These values remain in their native physics cards.

## MadGraph input

Each production uses one complete MadGraph input containing model import,
process definition, output, launch and run settings:

```text
import model ...
generate ...

output work/sample
launch work/sample

shower=OFF
detector=OFF
analysis=OFF
madspin=OFF
reweight=OFF

done

set nevents ...
set iseed ...
set ebeam1 ...
set ebeam2 ...
set pdlabel lhapdf
set lhaid ...

done
```

One FCC Event Runner invocation must produce exactly one LHE sample.

The MadGraph output must be a relative path inside the configuration
directory. Its basename becomes the output sample name:

```text
output work/ttbar
```

produces:

```text
outputs/ttbar.root
outputs/ttbar.metadata.json
```

## Pythia input

The Pythia card may use three runtime fields:

```text
@LHE_FILE@
@LHE_EVENTS@
@PYTHIA_SEED@
```

The runner replaces them with the generated LHE path, the actual LHE event
count and the Pythia seed. The user does not repeat these values in YAML.

## Optional checks

The following commands are optional. They are not required before a normal
production.

### Inspect without running

Show the resolved production summary without installing a PDF or generating
events:

```bash
./bin/fcc-run --dry-run examples/ttbar/config.yaml
```

### Prepare a batch environment

Check the Key4hep environment and install a missing PDF without generating
events:

```bash
./bin/fcc-run --prepare examples/ttbar/config.yaml
```

This is useful when compute nodes do not have external network access or when
many array jobs will use the same PDF set.

The normal production command performs this PDF check automatically, so
interactive users do not need to run `--prepare` first.

## LHAPDF storage

Missing PDF sets are installed by default in:

```text
$HOME/.local/share/fcc-event-runner/lhapdf
```

Select a different writable cache:

```bash
./bin/fcc-run \
  --lhapdf-dir "$HOME/softwares/lhapdf_data" \
  examples/ttbar/config.yaml
```

When a custom directory is used, pass the same option to `--prepare` and to
the actual production command:

```bash
./bin/fcc-run \
  --prepare \
  --lhapdf-dir "$HOME/softwares/lhapdf_data" \
  examples/ttbar/config.yaml

./bin/fcc-run \
  --lhapdf-dir "$HOME/softwares/lhapdf_data" \
  examples/ttbar/config.yaml
```

The cache is persistent and is reused by later productions.

## Confirmation

The default behavior is non-interactive. The runner prints a production
summary and starts immediately.

Require manual confirmation when running interactively:

```bash
./bin/fcc-run --confirm examples/ttbar/config.yaml
```

The runner then waits for:

```text
Press Enter to start or Ctrl+C to cancel:
```

## Existing outputs

Existing EDM4hep files are not replaced by default:

```text
ERROR: Output already exists: outputs/ttbar.root
```

Explicitly allow replacement:

```bash
./bin/fcc-run --overwrite examples/ttbar/config.yaml
```

The existing ROOT file remains untouched until the new output has been
generated and validated successfully.

## Intermediate files

The MadGraph process directory is removed after a successful production.
Failed process directories are preserved for debugging.

Keep the process directory after success:

```bash
./bin/fcc-run --keep-work examples/ttbar/config.yaml
```

Keep a compressed LHE output:

```bash
./bin/fcc-run --keep-lhe examples/ttbar/config.yaml
```

## EDM4hep validation

A production is considered successful only when:

1. MadGraph returns successfully.
2. Exactly one LHE sample is found.
3. The LHE file contains events.
4. Pythia8 and Delphes return successfully.
5. `podio-dump` can read the EDM4hep ROOT file.
6. The EDM4hep output contains at least one event.

The EDM4hep event count is not required to equal the requested MadGraph event
count. Matching or filtering may reduce the accepted event count.

## W+jets matching example

The W+jets example contains W+ and W- production with zero, one and two
matrix-element light partons.

MadGraph uses kT-MLM matching with:

```text
ickkw = 1
xqcut = 30 GeV
maxjetflavor = 4
```

Pythia uses:

```text
qCut = 45 GeV
nJetMax = 2
nQmatch = 4
```

These are example starting points, not validated FCC-hh production
parameters. Before a large production, inspect differential jet-rate
distributions, matching efficiency, veto fractions, cross sections and jet
observables for several matching-scale choices.

## Repository structure

```text
FCC-Event-Runner/
├── README.md
├── bin/
│   └── fcc-run
├── runner/
│   ├── workflow.py
│   ├── parsers.py
│   └── lhapdf.py
└── examples/
    ├── ttbar/
    │   ├── config.yaml
    │   ├── ttbar.mg5
    │   └── ttbar_pythia.cmd
    └── wjets/
        ├── config.yaml
        ├── wjets.mg5
        └── wjets_pythia.cmd
```

Users interact with `bin/fcc-run`. The complete FCC event-production sequence
is kept readable in `runner/workflow.py`; parsing and LHAPDF details are
separated into their corresponding helper files.

## Batch systems

FCC Event Runner contains no Slurm, TRUBA, HTCondor or CVMFSexec logic. A
batch script only loads Key4hep and calls:

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
- [MadGraph jet matching](https://cp3.irmp.ucl.ac.be/projects/madgraph/wiki/Matching)
- [Pythia8 JetMatching](https://pythia.org/manuals/pythia8204/JetMatching.html)