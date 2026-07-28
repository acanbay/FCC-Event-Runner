# Skimming

`fcc-skim` applies configurable object definitions and event preselections:

```text
EDM4hep ROOT -> FCCAnalyses preselections -> flat ROOT
```

The output is a compact flat analysis ntuple, not another EDM4hep file.

## Software environment

`fcc-skim` uses the active environment when `fccanalysis` is available.
Otherwise it loads `FCC_KEY4HEP_SETUP`, or
`/cvmfs/sw.hsf.org/key4hep/setup.sh` by default.

The command uses the podio DataSource and intentionally runs FCCAnalyses in
one thread.

## Required inputs

Run a skim with:

```bash
./bin/fcc-skim \
  input.root \
  output.root \
  path/to/skim.yaml
```

The input must be an EDM4hep ROOT file containing all collections named in the
skim YAML. The standard configuration requires:

| Purpose | Expected EDM4hep type |
|---|---|
| Jets | `ReconstructedParticleCollection` |
| Heavy-flavour tags | `ParticleIDCollection`, with one entry per jet |
| Electrons | `ReconstructedParticleCollection` |
| Muons | `ReconstructedParticleCollection` |
| Missing momentum | `ReconstructedParticleCollection` |
| Event weights | `EventHeaderCollection` named `EventHeader` |

When event generation uses selective EDM4hep output, these collections must
not be omitted. Missing collections cause FCCAnalyses to fail before producing
the flat ntuple.

Use `--dry-run` to validate paths and configuration and print the resolved
skim without processing events:

```bash
./bin/fcc-skim \
  --dry-run \
  input.root \
  output.root \
  path/to/skim.yaml
```

## YAML configuration

The complete configuration has two required sections:

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

### Object fields

All object fields are required.

| YAML field | Meaning | Constraint |
|---|---|---|
| `objects.jet.collection` | Input jet collection | Valid EDM4hep collection identifier |
| `objects.jet.pt_min` | Minimum jet transverse momentum in GeV | `>= 0` |
| `objects.jet.abs_eta_max` | Maximum absolute pseudorapidity for all selected jets | `> 0` |
| `objects.jet.central_abs_eta_max` | Upper boundary of the central-jet region | `> 0` |
| `objects.jet.forward_abs_eta_min` | Lower boundary of the forward-jet region | `>= central_abs_eta_max` |
| `objects.jet.forward_abs_eta_max` | Upper boundary of the forward-jet region | `> forward_abs_eta_min` and `<= abs_eta_max` |
| `objects.jet.btag.collection` | Jet heavy-flavour `ParticleID` collection | Same number and ordering as the jet collection |
| `objects.jet.btag.bit` | Working-point bit in the first tag parameter | Integer from `0` to `31` |
| `objects.electron.collection` | Input electron collection | Valid EDM4hep collection identifier |
| `objects.electron.pt_min` | Minimum electron transverse momentum in GeV | `>= 0` |
| `objects.electron.abs_eta_max` | Maximum electron absolute pseudorapidity | `> 0` |
| `objects.muon.collection` | Input muon collection | Valid EDM4hep collection identifier |
| `objects.muon.pt_min` | Minimum muon transverse momentum in GeV | `>= 0` |
| `objects.muon.abs_eta_max` | Maximum muon absolute pseudorapidity | `> 0` |
| `objects.MET.collection` | Input missing-momentum collection | Valid EDM4hep collection identifier |

The configured b-tag bit is detector-card dependent. In the included
`FCChh_II.tcl` example, bits `0`, `1` and `2` represent loose, medium and tight
working points.

### Object definitions

| Output object | Definition |
|---|---|
| `jet` | `pT >= pt_min` and `0 <= \|eta\| < abs_eta_max` |
| `central_jet` | `pT >= pt_min` and `\|eta\| < central_abs_eta_max` |
| `fjet` | `pT >= pt_min` and `forward_abs_eta_min <= \|eta\| < forward_abs_eta_max` |
| `bjet` | Central jet with the configured tag bit set |
| `electron` | `pT >= pt_min` and `\|eta\| < abs_eta_max` |
| `muon` | `pT >= pt_min` and `\|eta\| < abs_eta_max` |
| `lepton` | Merged selected electrons and muons |

Every object collection is sorted by decreasing transverse momentum. If the
central upper boundary equals the forward lower boundary, the two regions do
not overlap.

## Preselection language

`preselections` is a required non-empty YAML block string. Blank lines and
text after `#` are ignored.

### Variables

| Variable | Meaning |
|---|---|
| `jet_size` | Number of selected jets |
| `central_jet_size` | Number of selected central jets |
| `bjet_size` | Number of selected b-tagged central jets |
| `fjet_size` | Number of selected forward jets |
| `electron_size` | Number of selected electrons |
| `muon_size` | Number of selected muons |
| `lepton_size` | Number of selected electrons and muons combined |
| `MET` | Transverse momentum of the first missing-momentum object, or zero when the collection is empty |
| `mll` | Invariant mass of the selected dilepton pair, or `-1` when its size is not two |

Multiplicity, `MET` and `mll` selections support:

```text
>  >=  <  <=  ==
```

Multiplicity thresholds must be non-negative integers. `MET` and `mll`
thresholds cannot be negative.

### Dilepton charge

```text
SS
OS
```

`SS` requires a positive charge product and `OS` requires a negative charge
product. Either selection requires the configuration to contain:

```text
lepton_size == 2
```

### Dilepton-mass windows

```text
mll_window LOW HIGH include
mll_window LOW HIGH veto
```

`include` keeps the closed interval `[LOW, HIGH]`. `veto` removes that closed
interval. The limits must satisfy `0 <= LOW < HIGH`, and
`lepton_size == 2` is required.

Any supported selection may be omitted, but at least one active preselection
line is required. Unsupported syntax stops before FCCAnalyses starts.

### Common selection patterns

| Goal | Preselection form |
|---|---|
| Inclusive lepton charge | Omit `SS` and `OS`. |
| Same-sign dilepton selection | Use `lepton_size == 2` followed by `SS`. |
| Opposite-sign dilepton selection | Use `lepton_size == 2` followed by `OS`. |
| Select a dilepton mass region | Use `lepton_size == 2` and `mll_window LOW HIGH include`. |
| Reject a dilepton mass region | Use `lepton_size == 2` and `mll_window LOW HIGH veto`. |
| Apply only object multiplicities | Use any supported `*_size` comparisons and omit charge or mass lines. |

## Command options

| Option | Behaviour |
|---|---|
| `--dry-run` | Validate and summarize the skim without processing events. |
| `--overwrite` | Replace an existing output only after a successful skim. |

Input and output paths must differ. Without `--overwrite`, an existing output
causes an immediate error.

## Output branches

The flat ROOT output contains:

| Branches | Content |
|---|---|
| `event_weight` | Weight from the first `EventHeader`, or `1` when it is empty |
| `jet_size`, `central_jet_size`, `bjet_size`, `fjet_size` | Selected jet multiplicities |
| `electron_size`, `muon_size`, `lepton_size` | Selected lepton multiplicities |
| `MET` | Missing transverse momentum |
| `mll` | Dilepton invariant mass |
| `dilepton_charge_product` | Product of the two selected lepton charges |
| `<object>_pt`, `<object>_eta`, `<object>_phi`, `<object>_mass` | Kinematic arrays for `jet`, `central_jet`, `bjet`, `fjet`, `electron`, `muon` and `lepton` |
| `electron_charge`, `muon_charge`, `lepton_charge` | Charge arrays |

The output is first written to a temporary file and moved into place only
after FCCAnalyses completes successfully and produces a non-empty ROOT file.
The temporary file is removed on failure.

Generation metadata is not copied automatically. Preserve or associate the
input sample's metadata separately when it is needed for normalization.

See [`examples/skim`](../examples/skim) for a complete configuration.

## References

- [FCCAnalyses](https://hep-fcc.github.io/FCCAnalyses/)
- [EDM4hep](https://github.com/key4hep/EDM4hep)
