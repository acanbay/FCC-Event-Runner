# Skimming

`fcc-skim` applies configurable object definitions and preselections to an
EDM4hep file:

```text
EDM4hep ROOT -> FCCAnalyses preselections -> flat ROOT
```

Run a skim:

```bash
./bin/fcc-skim \
  input.root \
  output.root \
  path/to/skim.yaml
```

The output is a flat ROOT analysis ntuple, not another EDM4hep file.
`fcc-skim` uses the podio DataSource and runs FCCAnalyses in one thread.

## Configuration

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

Selected objects are ordered by transverse momentum. Central and forward jets
are defined by their configured absolute pseudorapidity ranges. B-tagged jets
must also satisfy the central-jet acceptance.

The b-tag `bit` selects a working-point bit stored in the configured
`ParticleID` collection. In the included `FCChh_II.tcl` example, bits 0, 1 and
2 correspond to loose, medium and tight working points.

## Preselection language

Supported multiplicities:

```text
jet_size
central_jet_size
bjet_size
fjet_size
electron_size
muon_size
lepton_size
```

Multiplicity, `MET` and `mll` selections support:

```text
>  >=  <  <=  ==
```

Dilepton charge is selected with `SS` or `OS`. Invariant-mass windows use:

```text
mll_window LOW HIGH include
mll_window LOW HIGH veto
```

`include` keeps the closed interval `[LOW, HIGH]`; `veto` removes it. `SS`,
`OS`, `mll` and `mll_window` require `lepton_size == 2` so that the dilepton
pair is unambiguous. Any supported line may be omitted, but the block must
contain at least one active selection. Blank lines and text after `#` are
ignored.

## Command options

| Option | Behaviour |
|---|---|
| `--dry-run` | Validate and summarize the skim without writing an output. |
| `--overwrite` | Replace an existing output only after the new skim succeeds. |

Input and output paths must be different. A temporary output is used during
processing and removed automatically if FCCAnalyses fails.

## Outputs

The flat ROOT tree contains:

- `event_weight`, `MET`, `mll` and `dilepton_charge_product`
- All supported object multiplicities
- `pt`, `eta`, `phi` and `mass` arrays for jets, central jets, b-jets, forward
  jets, electrons, muons and combined leptons
- Charge arrays for electrons, muons and combined leptons

See [`examples/skim`](../examples/skim) for a complete configuration.
