# Integrated demo data centre

Open **`demo-datacentre-01.usd-only.usda`** to inspect the complete usdAECO suite
stage without installing its plugins. The delivered facility has **3,009
elements, 41 spaces and three levels**, shared by all analyses. A [stock USD render](vanilla.png) is included.

| Form | File | Runtime |
|---|---|---|
| A | `demo-datacentre-01.usda` | ABI-matched `usdIfc` file-format reader |
| C | `demo-datacentre-01.usd-only.usda` | Stock USD; optional schema plugins enrich queries |

The flattened Form B is not supplied here. The source is
`usdaeco-datacentre v0.5.1`; the reader is `usdaeco-ifc v0.3.1`.

## Open, select and mute

Run these commands from the suite root:

```sh
usdview stage/demo-datacentre-01.usd-only.usda
usdview stage/views/shell.usda
usdview stage/views/architecture.usda
usdview stage/views/mep.usda
usdview stage/views/cctv.usda
usdview stage/views/plan-A.usda
usdview stage/views/plan-B.usda
```

Package views are `shell`, `site`, `architecture`, `structure`, `mep`,
`electrical`, `it`, `fitout` and `security`. Analysis views are `cctv`, `clash`,
`plan`, `plan-A`, `plan-B`, `compliance`, `repeat`, `solid`, `wall`, `pipe` and
`buildup`. `all` opens Form C. The `plan-A` and `plan-B` views span frames 0–77 at 24 fps;
the integrated root spans 0–288, including the CCTV tours.

In usdview's layer browser, mute `packages/cooling/cooling.usda` to remove that
delivery, or `analysis/cctv/root.usda` to remove the CCTV analysis. In Form A,
mute the corresponding `cooling.ifc` layer. Each package also has separately
mutable presentation, catalog drivers and, where needed, representation
placement layers. A study's display opinions remain independently selectable.

Open a different small root under `views/` to switch selections. Each package
view includes the shared spatial structure. Analysis views use the full
facility. Their cutaway visibility is in `presentation/views/`; the integrated
root keeps the delivered building visible. Cameras have distinct paths such as
`/Renders/cctv/overview` and `/Renders/plan/B`.

The spatial traversal starts at the site's actual path below
`/demo_datacentre_01`. The catalog and systems also sit below that project root.
The traversal utility reports levels, spaces, elements and the package owning
the defining spec; a stronger analysis overlay cannot claim ownership:

```sh
export PYTHON=python3
env -u PYTHONPATH "$PYTHON" tools/usdaeco_suite/traverse.py --summary
env -u PYTHONPATH "$PYTHON" tools/usdaeco_suite/traverse.py --package cooling
```

## Deliveries and layer order

`packages/` contains `shared`, `site`, `arch`, `structure`, `cooling`,
`electrical`, `it`, `fitout` and `security`. Each directory contains its IFC,
USD root, semantic layer, geometry crate, README and local overlays.
The shared delivery alone defines the spatial structure. Other deliveries
overlay it and define their elements, catalog types, systems and ports.

The 36 delivered IFC/USD files are copied byte for byte. Their source stamps
retain the original production tag, while the suite manifest records the
release that supplied those bytes. `dc.manifest.json` is the unchanged source
publication manifest. Package READMEs include the producer and measured census.

Strongest first, the roots compose presentation, analysis roots, then each
package's presentation, optional derived placement, catalog drivers and delivery.
Shared is last. Form A replaces each USD delivery with
`<discipline>.ifc:SDF_FORMAT_ARGS:spine=over&geometry=1`; shared uses ordinary
`shared.ifc`. All roots declare the union of 17 stock fallback types.

The IFC reader flattens each materialization. Package driver layers restore
catalog inheritance, and analysis inheritance overlays propagate introduced
type APIs to occurrences. This lets upper-layer type refinements reach both
forms. No copied delivery is rewritten. Bulk analysis geometry uses `.usdc` crates;
drivers, findings and small roots remain readable USDA.

Computed representation placements belong to their delivering package. They
use world anchors, retaining authored animation samples, so independently
muted analysis fragments do not remove another representation's placement.
Render camera definitions and their final poses live together in each analysis's
`cameras.usda`; presentation layers contain only visibility and display colour.
Programme pod relocation is restricted to programme views; the integrated
facility retains its delivered placement.

## Analyses and findings

| Analysis | Production |
|---|---|
| CCTV | Full-facility import, camera derivation and two coverage studies |
| Clash | Mesh study recomputed; committed exact bodies and exact findings retained |
| Plan | Both XER/MSPDI programmes recomputed; B selected in the integrated root |
| Compliance | Reader clauses evaluated; receipts refreshed against the final stack |
| Repeat | Floor comparison, reconstruction and quantities; quantities refreshed after other promotions |
| Solid | Committed exact result, rebased over the full facility |
| Wall | Wall promotion and office axes recomputed |
| Pipe | Pipe promotion and axis derivation recomputed |
| BuildUp | Wall recipes and representative layered bodies recomputed |
| Axis | Executed through the Wall and Pipe hooks; no standalone data-centre hook exists |

Each directory has `findings.json` and `receipt.json`. The latter compares the
real findings with the pinned example's expected shape; changed counts are
reported, not forced to match the smaller source fixture. `integration.json`
records computations refreshed against the final combined stack.

The released hooks contain fixture assumptions. The suite's bounded adapters
use the full publication's camera census, source hashes and counts, select
among multiple WC spaces, and exclude prototype-only spatial extents before
running Repeat's original reconstruction proof. The submodules are unchanged.

Exact material face subsets on `BrepArray` have no stock USD element domain;
the integration omits those material-only subsets, retaining the mesh twins'
appearance and the exact geometry. Empty material-binding opinions are omitted
and authored bindings declare `MaterialBindingAPI`. Equivalent world placement
changes refresh exact/twin correlation stamps without claiming new tessellation.

## Reproduce and verify

For computation, use the converter Python with USD 26.8, numpy, packaging,
IfcOpenShell, Pillow and the dependencies supplied by the pinned repositories.
No package installation is required. Source imports come from each submodule's
`tools/` directory.

Build `usdIfc` against an **existing** toolchain USD development output:

```sh
export USD_DEV="$USD_DEV_OUTPUT"
export BUILD_DIR="$PWD/hosts/usdaeco-ifc/out/build"
export PREFIX="$PWD/hosts/usdaeco-ifc/out"
bash hosts/usdaeco-ifc/build.sh
```

The native consumer and its Python must match that USD ABI. Select the existing
native schema and validator resources and a Python environment containing its
USD bindings, numpy and packaging:

```sh
export USDAECO_VALIDATION_PYTHON="$NATIVE_PYTHON"
export USDAECO_VALIDATION_PYTHONPATH="$NATIVE_PYTHON_SITE"
export USDAECO_NATIVE_PLUGINPATH="$USD_SOLID_SCHEMA/lib/usdSolid/resources:$USD_SOLID_VALIDATORS/lib/usdSolidValidators/resources"
export USD_SOLID_OCCT_RUNTIME="$EXACT_RUNTIME"
export AECO_EXACT_CACHE="$PWD/out/exact-cache"
export USDRECORD="$STOCK_USD/bin/usdrecord"
env -u PYTHONPATH "$PYTHON" stage/build.py
env -u PYTHONPATH "$PYTHON" stage/check.py --record --rebuild
env -u PYTHONPATH "$PYTHON" check.py
env -u PYTHONPATH "$PYTHON" -m pytest -q
```

These variables name existing outputs, not downloads. `NATIVE_PYTHON_SITE` is
a path list containing the matching USD, numpy and packaging modules. Use the
pinned `usdSolid` schema and validators. The exact runtime's `paths.json` supplies
its ABI-matched bridge consumer. The checker reads the IFC consumer Python
from `USD_DEV/pxrConfig.cmake` and keeps materialization caches under `out/`.
See the [reader setup](../hosts/usdaeco-ifc/docs/file-format.md).

To open Form A in a matching USD process:

```sh
export USDAECO_IFC_PYTHON="$PWD/hosts/usdaeco-ifc/tools/ifc-python"
export USDAECO_IFC_SOURCE_PYTHON="$PYTHON"
export USDAECO_IFC_CACHE="$PWD/out/ifc-cache"
export CORE_PLUGIN_DIR="$PWD/core/usdaeco-core/usdAeco"
export AXIS_PLUGIN_DIR="$PWD/section/usdaeco-axis/usdAecoAxis"
export PXR_PLUGINPATH_NAME="$PWD/hosts/usdaeco-ifc/out/plugins/usdIfc/resources"
usdview stage/demo-datacentre-01.usda
```

Optional schema registration is performed before opening stages, with core
first. The source resource directories are used directly; only the IFC reader
and native kit libraries require compiled binaries.

`stage/build.py --smoke` selects CCTV only. `--output` builds a separate copy.
The development option `--reuse-hooks` only rearchives existing work; it is not
a reconstruction proof. Normal builds rerun hooks. The checker can reuse a
successful probe with `--use-evidence` only when its stage, probe code and runtime
receipt match. `--rebuild` reruns the hooks and compares all text layers. If a separate build
has just completed, `--compare-rebuild out/stage-rebuilt` compares that output
without repeating its computations.

## Acceptance and deviations

The manifest contains the measured prim and mesh census, per-rule warnings,
per-layer mute table (default and authored transform samples), strict checker result, plugin-free render and byte comparison.
Copied source hashes, every authored layer's role and producer, and file sizes
are checked. The stage cap is 80,000,000 bytes; each analysis USDA is capped at
2,000,000 bytes and each analysis publication at 10,000,000 bytes.

| Measured proof | Result |
|---|---:|
| Connected and USD-only prims | 15,576 each; identical |
| Compared meshes | 3,583; two declared exclusions |
| Plugin-free views | 21 |
| Registered validators executed | 124 |
| Unexpected integration errors | 0 |
| Expected findings (error severity) | 55 |
| Animated prims / transform samples | 19 / 109 |
| Mute cases / placement changes | 117 / 0 |
| Predicted and observed dangling port sites | 1,008 each |
| Stage gate | 10 checks, 0 failed |
| Text layers in the rebuild comparison | 177 |
| Source gate | 56 checks, 0 failed |
| Pytest | 43 passed |

The published analyses encode expected findings with validator error severity:
2 `MisplacedDevice` results from Compliance and 53 `RepeatDrift` results from
Repeat. `expectedFindings` names each rule, count, producing library and its
`integrated-findings.json`. The gate independently cross-checks those analysis
findings and requires the validator error multiset to match exactly. Any extra
error, including `ComplianceStale`, fails. The final full-plugin computation
has no stale compliance receipts; `integrationFindings` is empty.

The mute table covers 97 used layers (including 19 empty layers) and 20
view-only layers absent from the integrated stack. Sixty cases expose
additional analysis dependency errors.

Muting source or analysis dependencies can invalidate persisted derived receipts
and proxy links. The mute table retains those diagnostic counts separately from
composition, transform changes and the source manifest's predicted cross-package
port links. This is a deviation from the port-only diagnostic requirement; it does not
claim that a muted study remains current.

Nine upstream USD source stamps (the three twin layers for cooling, electrical
and IT) do not match their delivered IFC hashes. Those source bytes are retained
exactly; `sourceStampDifferences` records the mismatch separately from the
verified copy hashes and the suite-authored provenance.

The exact producer hooks remain tied to their original native generation
recipes; their committed results are identified explicitly. Full-facility exact
recomputation is not proven. Nix packaging is not proven: the single attempt
stopped at a public input lookup returning HTTP 404. The measured stock CPU
renderer uses USD 25.05.01; connected reads and strict checks use the supplied
USD 26.11 runtime, while plugin-free composition is also checked with USD 26.8.
