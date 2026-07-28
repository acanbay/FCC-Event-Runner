# Event Generation

`fcc-run` executes:

```text
MadGraph5 -> LHE -> Pythia8 -> Delphes -> EDM4hep ROOT
```

It keeps physics settings in their native MadGraph, Pythia and Delphes cards
and uses one YAML file to connect them.

## Software environment

`fcc-run` uses the active Key4hep environment when `mg5_aMC`,
`DelphesPythia8_EDM4HEP` and `podio-dump` are already available. Otherwise it
loads `FCC_KEY4HEP_SETUP`, or `/cvmfs/sw.hsf.org/key4hep/setup.sh` when that
variable is not set.

The runner does not install Key4hep or mount CVMFS. The setup file and its
software repositories must already be accessible on the execution host.

## Required production files

Each production requires one YAML manifest, one MadGraph card and one Pythia
card:

```text
sample/
|-- config.yaml
|-- sample.mg5
`-- sample_pythia.cmd
```

The minimal YAML connects the required cards:

```yaml
madgraph_card: sample.mg5
pythia_card: sample_pythia.cmd
delphes_card: ${DELPHES_DIR}/cards/FCC/scenarios/FCChh_II.tcl
```

Relative paths are resolved from the YAML directory. Environment variables and
home-directory references are expanded. No EDM4hep output field is required
for a normal production.

Run the production with:

```bash
./bin/fcc-run path/to/config.yaml
```

Use `--dry-run` first to resolve and validate the configuration without
writing files:

```bash
./bin/fcc-run --dry-run path/to/config.yaml
```

## MadGraph card

The native MadGraph card is the single source for:

- Model, process and decay definitions
- Generation cuts
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

Its basename defines the sample name and therefore the final
`sample_name.root` and `sample_name.metadata.json` filenames.

MadGraph showering, detector simulation and analysis must remain disabled
because Pythia8 and Delphes are executed explicitly by `fcc-run`.

## Pythia card

The Pythia card owns showering, hadronization and matching settings. It may use
these runtime fields:

| Field | Runtime value |
|---|---|
| `@LHE_FILE@` | Generated uncompressed LHE path |
| `@LHE_EVENTS@` | Number of events found in the LHE file |
| `@PYTHIA_SEED@` | Seed derived from the MadGraph seed |

An unresolved `@FIELD@` stops before Pythia8 starts.

For matching, MadGraph and Pythia settings must describe the same scheme and
scales. See [`examples/wjets`](../examples/wjets) for a kT-MLM configuration.
Its demonstration scales must be validated for the intended production.

## Detector and default EDM4hep output

The required `delphes_card` field selects the detector simulation. Any
standard FCC Delphes card may be supplied:

```yaml
delphes_card: ${DELPHES_DIR}/cards/FCC/scenarios/FCChh_II.tcl
```

When no optional EDM4hep field is present, `fcc-run` uses:

```text
${K4SIMDELPHES}/edm4hep_output_config.tcl
```

This is the normal configuration and is sufficient for a complete
production.

## Optional EDM4hep output control

Optional output settings belong in the same production YAML. A separate YAML
is not created for reduced output.

| YAML content | Behaviour |
|---|---|
| Neither optional field | Use the standard `${K4SIMDELPHES}/edm4hep_output_config.tcl` card. |
| `edm4hep_card` | Use the supplied complete k4SimDelphes output card. |
| `edm4hep_output` | Generate one runtime output card from selected `TreeWriter` branches. |

`edm4hep_card` and `edm4hep_output` cannot be used together.

To use another complete output definition:

```yaml
edm4hep_card: /path/to/custom_edm4hep_output.tcl
```

To persist only selected Delphes branches:

```yaml
edm4hep_output:
  collections:
    - EFlowTrack
    - EFlowPhoton
    - EFlowNeutralHadron
    - Electron
    - Muon
    - Jet
    - MissingET
```

See [`examples/ttbar-output-selection`](../examples/ttbar-output-selection)
for a directly runnable selective-output production.

### How collection selection works

Before event generation, `fcc-run`:

1. Reads the `TreeWriter` branches from the selected Delphes detector card.
2. Resolves every requested collection by its `BranchName`.
3. Maps its `BranchClass` to the corresponding k4SimDelphes conversion group.
4. Writes a runtime EDM4hep output card and passes it to
   `DelphesPythia8_EDM4HEP`.

The detector card is not modified, and all detector-simulation modules still
run. The generated output card and resolved collection list are preserved in
the production logs and metadata.

### Why select collections?

Delphes still executes the complete detector simulation. Selection only
controls which simulated objects are converted and persisted in the final
EDM4hep ROOT file. Omitting unused truth, reconstructed-object or event-level
collections can substantially reduce storage and later input time.

The entries are `BranchName` values read dynamically from the `TreeWriter`
section of the selected detector card. In:

```tcl
add Branch ECal/eflowPhotons EFlowPhoton Tower
```

the selectable name is `EFlowPhoton`. `ECal/eflowPhotons` is the Delphes input
array, not the output name. Names may differ between detector cards; unknown
names produce an error that also reports the available branches.

### Supported TreeWriter classes

The table describes every `BranchClass` that the runner can convert. Example
names are common FCC card conventions; the actual selectable names always
come from the chosen detector card.

| `BranchClass` | Typical `BranchName` examples | EDM4hep content when selected | Effect when omitted |
|---|---|---|---|
| `GenParticle` | `Particle` | A same-named `MCParticle` collection used for truth information and reconstruction links. | Generator-level particles are not persisted; useful truth associations are unavailable. |
| `Track` | `Track`, `EFlowTrack` | Entries in the global `ReconstructedParticles` collection with an associated same-named `Track` collection. | That track-based reconstructed-particle source is absent. |
| `Tower` | `Tower`, `EFlowPhoton`, `EFlowNeutralHadron` | Entries in the global reconstructed-particle collection with an associated same-named `Cluster` collection. Supporting calorimeter-hit data may also be written. | That calorimeter-based reconstructed-particle source is absent. |
| `ParticleFlowCandidate` | Card dependent | A separate same-named `ReconstructedParticle` collection. | That particle-flow candidate collection is absent. |
| `Jet` | `GenJet`, `Jet`, `ExclusiveJets_N2` | A same-named `ReconstructedParticle` collection with available flavour and tau tag information. | The jet collection and its tag information are absent. |
| `Muon` | `Muon` | A same-named subset of the global reconstructed-particle collection and its isolation values. | The identified-muon collection is absent. |
| `Electron` | `Electron` | A same-named subset of the global reconstructed-particle collection and its isolation values. | The identified-electron collection is absent. |
| `Photon` | `Photon` | A same-named subset of the global reconstructed-particle collection and its isolation values. | The identified-photon collection is absent. |
| `MissingET` | `GenMissingET`, `MissingET` | A same-named `ReconstructedParticle` collection containing one missing-momentum object per event. | That missing-momentum collection is absent. |
| `ScalarHT` | `ScalarHT` | A same-named float collection containing one scalar-HT value per event. | That scalar-HT collection is absent. |

`EventHeader` is produced by the Pythia8 reader and is not selected through
the `TreeWriter` list. Converter support collections such as
`ReconstructedParticles`, `RecoMCLink`, tracker hits and calorimeter hits may
also appear when required by selected reconstructed objects.

### Selection dependencies

- `Electron`, `Muon` and `Photon` are subset collections. At least one
  `Track`, `Tower` or `ParticleFlowCandidate` branch must also be selected.
- A `Jet` branch may be written without reconstructed-particle sources, but
  its persisted constituent links will be absent. The runner prints a warning.
- k4SimDelphes assumes that selected `Track` and `Tower` sources form a
  non-overlapping particle list. Avoid combinations that double count the
  same reconstructed objects.
- Unsupported Delphes classes, duplicate names and names absent from the
  selected detector card stop before MadGraph starts.
- The detector card must use the standard
  `add Branch InputArray BranchName BranchClass` form in its `TreeWriter`
  module.

### Common usage scenarios

| Goal | Configuration |
|---|---|
| Standard complete output | Omit both optional EDM4hep fields. |
| Existing experiment-specific output definition | Set `edm4hep_card`. |
| Reconstruction-only analysis | Select the required reconstructed sources, identified objects, jets and event-level quantities; omit the `GenParticle` branch. |
| Preserve truth matching | Include the detector card's required `GenParticle` branch, commonly `Particle`. |
| Preserve jet constituents | Include the jet collection and the reconstructed-particle sources used to build it. |
| Event counting only | Use `collections: []`; the output contains `EventHeader` without selected TreeWriter collections. |

The generated runtime card is stored in the production log directory, and the
selected branch names are recorded in metadata.

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

The cache is placed before existing LHAPDF search paths, so missing sets are
installed without modifying read-only software installations. `--prepare`
performs the installation and exits before event generation.

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

`--dry-run` and `--prepare` are mutually exclusive. `--confirm` requires an
interactive terminal and should not be used in batch jobs.

## Outputs and validation

A successful production writes:

```text
outputs/<sample>.root
outputs/<sample>.metadata.json
logs/<sample>/<UTC timestamp>/
```

The EDM4hep output is first written to a temporary file. It is moved into its
final location only when `podio-dump` succeeds and reports at least one event.
The final event count may differ from the requested MadGraph count after
matching or filtering.

The metadata JSON records:

- Requested, LHE and EDM4hep event counts
- LHE and Pythia cross sections and their uncertainties
- Which cross section is used for normalization
- Matching efficiency when matching is enabled
- Beam energies, LHAPDF ID and matching mode
- MadGraph and Pythia seeds
- Input cards, selected Delphes branches and executable paths

For MLM or FxFx samples, `cross_section_pb` is the post-matching cross section
reported by Pythia8. For unmatched samples it is the LHE cross section. The
explicit `lhe_cross_section_pb`, `pythia_cross_section_pb`,
`cross_section_source` and `matching_efficiency` fields preserve the
normalization provenance.

Logs contain MadGraph, Pythia/Delphes and validation output together with the
resolved run card, parameter card, banner and any generated EDM4hep output
card.

Successful MadGraph work directories are removed unless `--keep-work` is
used. Failed MadGraph directories are preserved for diagnosis. Existing final
outputs are not replaced unless `--overwrite` is used.

## Examples

- [`examples/ttbar`](../examples/ttbar) demonstrates production without jet
  matching.
- [`examples/wjets`](../examples/wjets) demonstrates kT-MLM matching.
- [`examples/ttbar-output-selection`](../examples/ttbar-output-selection)
  demonstrates a self-contained production with selective EDM4hep
  persistence.

## References

- [FCC Software](https://hep-fcc.github.io/FCCSW/)
- [k4SimDelphes output configuration](https://github.com/key4hep/k4SimDelphes/blob/main/doc/output_config.md)
- [Delphes TreeWriter](https://delphes.github.io/workbook/modules/)
