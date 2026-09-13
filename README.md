# usdaeco — the usdAECO suite

The usdAECO suite brings 23 released repositories into one Git superproject:
schema domains, tools, integrations, data, checks and the [HTML guide](docs/index.html).
[suite.json](suite.json) selects release train `aeco-0.8.1`; Git records each
submodule's full commit ID. The [suite map](docs/suite.md) links every README
and documentation folder.

## Use case

Use one checkout to navigate the suite and reproduce its selected releases.
Submodules keep each repository independently versioned. The directory tiers
make their roles visible; they do not introduce a second USD spatial hierarchy.

The planned integrated example follows a construction delivery: one shared
spatial structure, discipline packages such as architecture and cooling, then
analyses and presentation layers. Each package carries its delivered IFC file
beside a USD twin. A producer stamp records whether a package came from a
generator, Revit or Bonsai; all three use the same IFC delivery route.

## The schema on an index card

The suite introduces no schema. Its schema domains extend the closed core
through applied APIs: one identity, kind through classification, drivers as
inputs and derived geometry as outputs. Namespace describes location, layers
describe delivery and ownership, and collections describe groups. See the
[design model](core/usdaeco-core/docs/03-design-model.md) and
[schema reference](core/usdaeco-core/docs/04-schema-reference.md).

## The example

The [integrated stage](stage/README.md) is **not built yet**. The contract
defines three forms of `demo-datacentre-01`: a connected root reading IFC
packages through `usdIfc`, a self-contained flattened crate, and the same
layer stack over USD twins that composes without plugins. Discipline and
analysis layers can be muted independently, with shared transforms preserved.

The target facility combines the base, extra floors, pods, planted pipe clashes
and security readers into one federated `full` variant. The pinned data release
currently supplies the separate variants. Existing examples remain available
through the submodule READMEs in the [suite map](docs/suite.md).

## Build and check

Clone from your Git service's suite URL:

```sh
git clone --recurse-submodules <suite-repository-url> usdaeco
cd usdaeco
```

For an existing clone, run `git submodule update --init --recursive`.
Relative submodule URLs resolve against the superproject's origin. Public
publication must translate gitlinks to the corresponding public tag commits
and the two geometry-kit URLs to their public owner before distributing a clone.

Use an existing Python 3.11+ environment with pytest and Pillow. Run directly
from source; tests insert `tools/` into `sys.path`, with no installed package
or setuptools dependency. The source gate does not build submodules or load USD.

```sh
export PYTHON=python3
env -u PYTHONPATH "$PYTHON" check.py
env -u PYTHONPATH "$PYTHON" -m pytest -q
env -u PYTHONPATH "$PYTHON" tools/usdaeco_suite/pins.py --check
env -u PYTHONPATH "$PYTHON" tools/usdaeco_suite/checkout.py
```

The gate prints `N checks, M failed, K not run`. It checks the release index,
submodule HEADs and gitlinks, generated metadata, matching flake tags, local
documentation links, site assets, sanitization and version agreement. The
checkout command reports every pin; `--apply` restores clean submodules to the
recorded tags after preflighting all of them. It never fetches or discards edits.
The root `build.sh` currently runs pin freshness and source verification only;
it explicitly reports that the integrated stage is not built yet.

Nix inputs use public release tags. The dev shell selects the schema toolchain's
Python environment. To evaluate the pin assertion without package builds:

```sh
nix flake check --no-write-lock-file --no-build
nix develop
```

For private mirrors, follow the toolchain's
[external registry and input-override instructions](kits/usdaeco-toolchain/README.md#build-and-check).
Keep deployment mappings outside the checkout and do not commit a lockfile.
Nix resolution and shell availability are reported separately in
[verification notes](docs/verification.md).

To update a pin, fetch the desired release into its submodule and check out its
tag, for example `git -C section/usdaeco-axis checkout --detach refs/tags/<tag>`.
Then regenerate the suite, flake input block and documentation map:

```sh
env -u PYTHONPATH "$PYTHON" tools/usdaeco_suite/pins.py
git add section/usdaeco-axis suite.json flake.nix docs/suite.md
env -u PYTHONPATH "$PYTHON" check.py
env -u PYTHONPATH "$PYTHON" -m pytest -q
```

Stage the gitlink before checking: the gate compares the recorded index to
HEAD. Pins must form a released train; advance `gate/usdaeco-scenarios` to the
release whose index names the new tags, update the affected submodules, and
regenerate together. An isolated tag bump against an older train fails by design.

## Suite

Each entry in [suite.json](suite.json) records the repository, path, layout
tier, repository kind, schema domain (or null), exact tag and supported
requirements. Layout tiers group integrations under `hosts`, tools under
`kits`, and release checks under `gate`; repository kinds retain their original
metadata values. The generator reads `library.json` and resolves the tag inside
each submodule. The older `aeco-toolchain` release has no root metadata, so its
entry uses the scenarios release-index card.

The [HTML guide](docs/index.html) explains the schema domains; the
[repository map](docs/suite.md) covers the whole suite. The source checker
adapts S01–S05 and S25 for the suite kind, release list and relative kit URLs.
The remaining skeleton rules use the pinned toolchain; schema/example-only
rules report their inapplicability. See [verification notes](docs/verification.md).

## Layout

| Path | Contents |
|---|---|
| core/ | Closed built-environment schema domain |
| section/ | Shared path and layered-section schema domains |
| kind/ | Element and analysis schema domains and examples |
| record/ | Host synchronization records |
| hosts/ | IFC, Revit and Bonsai integrations |
| kits/ | Build/check tools, execution and exact-geometry kits |
| data/ | Released demo facility variants |
| gate/ | Release scenarios and suite board |
| docs/ | HTML guide, suite map and verification notes |
| stage/ | Planned integrated-stage contract |
| tools/usdaeco_suite/ | Source utilities |
| tests/ | Source-only pytest checks |
| testenv/ | Standalone smoke entry point |
| suite.json | Generated release pins and supported requirements |
| flake.nix | Matching inputs, evaluated pin assertion and Python shell |
| build.sh | Source verification entry point; stage build remains planned |

## Status

Version 0.1.0 supplies the superproject and documentation. It proves release
pin consistency and source structure. Integrated composition, conversion,
rendering, muting, flattening and reconstruction are not proven by this release;
their required acceptance checks are in the [stage contract](stage/README.md).

## Licence

[MIT](LICENSE). Each submodule retains its own licence and dependency terms,
documented in its README. The suite's licence does not replace them.
