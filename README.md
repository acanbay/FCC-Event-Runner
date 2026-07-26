# FCC Event Runner

FCC Event Runner is a lightweight workflow for private FCC event production
with the Key4hep software stack.

It runs the following chain:

```text
MadGraph5_aMC@NLO -> LHE -> Pythia8 -> Delphes -> EDM4hep ROOT
```

FCC Event Runner does not define physics parameters. The complete physics
configuration remains in the MadGraph, Pythia and Delphes cards.

## Requirements

FCC Event Runner must be used inside a loaded Key4hep environment.

Example:

```bash
source /cvmfs/sw.hsf.org/key4hep/setup.sh -r 2026-04-08
```

The following commands must be available:

```text
mg5_aMC
DelphesPythia8_EDM4HEP
podio-dump
lhapdf
lhapdf-config
```

No separate Python package installation or virtual environment is required.
The YAML reader is expected to be available in the Key4hep Python
environment.

Make the launcher executable after cloning the repository:

```bash
chmod +x bin/fcc-run
```

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

Users interact only with `bin/fcc-run`.

The complete FCC production sequence is visible in:

```text
runner/workflow.py
```

## Production configuration

The YAML file only connects the input cards:

```yaml
madgraph_card: process.mg5
pythia_card: pythia.cmd
delphes_card: ${DELPHES_DIR}/cards/FCC/scenarios/FCChh_II.tcl
edm4hep_card: ${K4SIMDELPHES}/edm4hep_output_config.tcl
```

Physics parameters are not duplicated in YAML.

The following settings remain in the single MadGraph card:

- Physics model
- Process definition
- MadGraph output directory
- Event count
- Random seed
- Beam energies
- LHAPDF ID
- Generation cuts
- Matching parameters
- Model parameters

Pythia showering and matching parameters remain in the Pythia card.

## MadGraph card requirement

The MadGraph input must contain the complete generation and launch sequence:

```text
import model ...
generate ...
output work/sample
launch work/sample

...

done

set nevents ...
set ebeam1 ...
set ebeam2 ...
set pdlabel lhapdf
set lhaid ...

done
```

One FCC Event Runner invocation must produce exactly one LHE sample.

The MadGraph output must be a relative path inside the configuration
directory. The basename of the MadGraph output becomes the sample name.

For:

```text
output work/ttbar
```

the final outputs are:

```text
outputs/ttbar.root
outputs/ttbar.metadata.json
```

## Pythia card fields

The Pythia card may use three runtime fields:

```text
@LHE_FILE@
@LHE_EVENTS@
@PYTHIA_SEED@
```

They are resolved automatically after MadGraph finishes.

The user does not repeat the event count or LHE path in YAML.

## Running the examples

Prepare the Key4hep environment and the requested PDF:

```bash
./bin/fcc-run --prepare examples/ttbar/config.yaml
```

Inspect the resolved production without running anything:

```bash
./bin/fcc-run --dry-run examples/ttbar/config.yaml
```

Run the ttbar example:

```bash
./bin/fcc-run examples/ttbar/config.yaml
```

Run the W+jets example:

```bash
./bin/fcc-run examples/wjets/config.yaml
```

## Confirmation

The default behavior is non-interactive. FCC Event Runner prints the
production summary and starts immediately.

To require confirmation:

```bash
./bin/fcc-run --confirm examples/ttbar/config.yaml
```

The runner waits for Enter:

```text
Press Enter to start or Ctrl+C to cancel:
```

## Existing outputs

Existing EDM4hep files are not replaced by default.

To replace an existing output after the new file passes validation:

```bash
./bin/fcc-run --overwrite examples/ttbar/config.yaml
```

The old ROOT file remains untouched until the new output has been generated
and validated successfully.

## Intermediate files

The MadGraph process directory is removed after a successful production.

Keep it with:

```bash
./bin/fcc-run --keep-work examples/ttbar/config.yaml
```

Failed process directories are always preserved.

The LHE file is removed with the MadGraph process directory by default.

Keep a compressed LHE output with:

```bash
./bin/fcc-run --keep-lhe examples/ttbar/config.yaml
```

## LHAPDF

The runner reads `lhaid` directly from the MadGraph card.

It first searches the LHAPDF paths provided by Key4hep. If the requested set is
missing, it is installed in:

```text
$HOME/.local/share/fcc-event-runner/lhapdf
```

A different writable directory can be selected with:

```bash
./bin/fcc-run \
  --lhapdf-dir /path/to/lhapdf_data \
  config.yaml
```

Run `--prepare` before submitting batch jobs when compute nodes do not have
external network access.

## EDM4hep validation

A production is successful only when:

1. MadGraph returns successfully.
2. An LHE file is found.
3. The LHE file contains events.
4. Pythia8 and Delphes return successfully.
5. `podio-dump` can read the EDM4hep ROOT file.
6. The EDM4hep output contains at least one event.

The output event count is not required to equal the requested MadGraph event
count. Matching or filtering may reduce the number of accepted events.

## W+jets matching example

The W+jets example contains W+ and W- production with zero, one and two
matrix-element light partons.

The MadGraph card uses kT-MLM matching with:

```text
ickkw = 1
xqcut = 30 GeV
maxjetflavor = 4
```

The Pythia card uses:

```text
qCut = 45 GeV
nJetMax = 2
nQmatch = 4
```

These values are example starting points, not validated FCC-hh production
parameters.

Before a large production:

1. Generate small samples with several matching-scale choices.
2. Inspect the differential jet-rate distributions.
3. Check that the transition region is smooth.
4. Inspect the matching efficiency and veto fraction.
5. Compare post-matching cross sections and jet observables.

## Batch systems

FCC Event Runner contains no Slurm, TRUBA, HTCondor or CVMFSexec logic.

A batch script only needs to load Key4hep and call:

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