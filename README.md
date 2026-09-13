# usdaeco — the usdAECO suite

The usdAECO suite brings 23 released repositories into one Git superproject:
schema domains, tools, integrations, a federated demo facility and the
[HTML guide](docs/index.html). [suite.json](suite.json) lists the pins;
[the suite map](docs/suite.md) links their documentation.

## Use case

Open and inspect one building assembled from independently delivered packages,
then select its security, clash, programme, compliance or representation studies.
Every discipline has an IFC delivery beside its USD twin. The layer stack records
who supplied each delivery and which library produced each analysis.

## The schema on an index card

The suite introduces no schema. Its domains extend the closed core through
applied APIs: one identity, kind through classification, drivers as inputs and
representations as outputs. Namespace describes location, layers describe
ownership, and collections describe groups. See the
[design model](core/usdaeco-core/docs/03-design-model.md) and
[schema reference](core/usdaeco-core/docs/04-schema-reference.md).

## The example

The [integrated stage](stage/README.md) contains the `full` facility: three
storeys, 41 spaces and 3,009 elements, delivered as a shared spatial structure
and eight discipline packages. Nine analysis directories contain recomputed
studies and explicitly identified committed exact results.

```sh
usdview stage/demo-datacentre-01.usd-only.usda
usdview stage/views/architecture.usda
usdview stage/views/plan-B.usda
```

Form C uses portable USD twins and opens without suite plugins. Form A,
`stage/demo-datacentre-01.usda`, substitutes delivered IFC through the `usdIfc`
reader. Both use the same analysis and presentation stack. Form B,
`stage/demo-datacentre-01.flat.usdc`, is a self-contained flattened crate that
opens alone in stock USD. Cooling was delivered through Bonsai; its comparison
receipt proves the identities, document links and converted scene survived.

## Build and check

Clone from your Git service's suite URL:

```sh
git clone --recurse-submodules <suite-repository-url> usdaeco
cd usdaeco
export PYTHON=python3
env -u PYTHONPATH "$PYTHON" check.py
env -u PYTHONPATH "$PYTHON" -m pytest -q
```

For an existing clone, run `git submodule update --init --recursive`.
Relative URLs resolve against the superproject's origin. Public publication
must translate gitlinks to the corresponding public tag commits and translate
the two geometry-kit URLs to their public owner.

Use Python 3.11+ with pytest and Pillow for source checks. Stage computation
also needs USD 26.8, numpy, packaging and the execution dependencies described
in the pinned repositories. Run from source; tests insert `tools/` into
`sys.path` and require no installed package or setuptools.

The [stage guide](stage/README.md) explains native runtime selection and the
complete build and proof commands. After configuring those existing runtimes:

```sh
env -u PYTHONPATH "$PYTHON" stage/build.py
env -u PYTHONPATH "$PYTHON" stage/check.py --record --rebuild
env -u PYTHONPATH "$PYTHON" tools/usdaeco_suite/traverse.py --summary
```

Both gates print `N checks, M failed`. The source gate verifies pins, structure,
versions, documentation links and sanitization. The stage gate records composition,
reader parity, validators, mute drills, rendering, inventory and reproduction.
Illustrative domain errors retain their original severities; their counts and
acceptance deviations are documented in the stage guide and manifest.

`build.sh` verifies the source and builds Forms A and C. Nix inputs use public
release tags. The measured Nix attempt failed to resolve a public input;
Nix packaging remains not proven. Follow the toolchain's
[external registry instructions](kits/usdaeco-toolchain/README.md#build-and-check)
for local mirrors. Do not commit a lockfile.

To change a pin, fetch and check out its released tag, update any explicit
[suite advance](suite-overrides.json), and regenerate the metadata:

```sh
env -u PYTHONPATH "$PYTHON" tools/usdaeco_suite/pins.py
git add suite.json flake.nix docs/suite.md <changed-submodule-path>
env -u PYTHONPATH "$PYTHON" check.py
```

Stage the gitlink before checking: the gate compares the index to HEAD.
`tools/usdaeco_suite/checkout.py` reports every pin; `--apply` restores clean
submodules only after preflighting the entire selection. It never fetches or
discards edits.

## Suite

The baseline is release train `aeco-0.8.1`. Two explicit advances select the
federated data release `v0.5.1` and IFC reader `v0.3.1`.
Each override records a released tag, its full revision and a reason.
Other pins must still agree with the baseline index.

Each generated entry records its path, tier, repository kind, schema domain,
exact tag and supported requirements. `library.json` supplies metadata; the
older processing-toolchain kit uses its release-index card. All 23 submodules
remain independent repositories at their recorded tags.

## Layout

| Path | Contents |
|---|---|
| core/ | Closed built-environment schema domain |
| section/ | Shared path and layered-section domains |
| kind/ | Element and analysis domains and examples |
| record/ | Host synchronization records |
| hosts/ | IFC, Revit and Bonsai integrations |
| kits/ | Build/check, execution and exact-geometry tools |
| data/ | Released demo facility |
| gate/ | Release scenarios and suite board |
| docs/ | HTML guide, suite map and verification notes |
| stage/ | Connected, flattened and USD-only forms, deliveries, analyses, views and proofs |
| tools/usdaeco_suite/ | Pin, build, traversal and verification utilities |
| tests/ | Tests executed directly from source |
| testenv/ | Standalone source smoke entry point |
| suite.json | Generated repository pins |
| suite-overrides.json | Explicit advances beyond the baseline train |
| flake.nix | Matching public inputs and Python shell |
| build.sh | Source verification and stage build |

## Status

Version 0.4.0 adds [Working with the integrated stage](docs/stage/index.html)
and a checkout walkthrough in the documentation hub. The guide connects forms,
deliveries, traversal and views to the published evidence. The stage remains the
0.3.0 artifact; its [reference](stage/README.md) records what was run, what uses
committed results, and the limits of expected analysis findings and mute-validation
deviations. The complete measured record is [stage/manifest.json](stage/manifest.json).

## Licence

[MIT](LICENSE). Each submodule retains its own licence and dependency terms,
documented in its README. The suite's licence does not replace them.
