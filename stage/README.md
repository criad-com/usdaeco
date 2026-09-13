# Integrated demo data centre

Open **`demo-datacentre-01.usd-only.usda`** to inspect the complete usdAECO suite
stage without installing its plugins. The delivered facility has **3,009
elements, 41 spaces and three levels**, shared by all analyses. A [stock USD render](vanilla.png) is included.

| Form | File | Runtime |
|---|---|---|
| A | `demo-datacentre-01.usda` | ABI-matched `usdIfc` file-format reader |
| B | `demo-datacentre-01.flat.usdc` | Stock USD; one self-contained crate |
| C | `demo-datacentre-01.usd-only.usda` | Stock USD; optional schema plugins enrich queries |

The source is
`usdaeco-datacentre v0.6.0`; the reader is `usdaeco-ifc v0.3.1`.

The integrated root contains exactly three prims:

```text
/demo_datacentre_01
  _TypeCatalog
  demo_datacentre_01_Site
/Studies
  cctv clash plan compliance repeat solid wall pipe buildup
/Renders
  <library>/<camera>
```

`/Studies` is a plain Scope. All analysis additions outside the building live
under `/Studies/<library>`, including materials, target grids, findings,
programmes, specifications and exact prototypes. The one catalog is
`/demo_datacentre_01/_TypeCatalog`; Pipe adds its classes there. A referenced
project therefore carries its catalog. There is no root-level `/_TypeCatalog`.

## Walking the building

Run these commands from the suite root:

```sh
usdview stage/demo-datacentre-01.usd-only.usda
usdview stage/demo-datacentre-01.flat.usdc
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

The summary reports these delivering element counts (3,009 in total):

```text
== stage: delivered element census
packages/arch: 167
packages/cooling: 737
packages/electrical: 1254
packages/fitout: 23
packages/it: 671
packages/security: 70
packages/shared: 0
packages/site: 3
packages/structure: 84
```

`--package cooling` retains spatial ancestors, so a real excerpt reads:

```text
demo_datacentre_01_Site [packages/shared]
  demo_datacentre_01 [packages/shared]
    L01_Office [packages/shared]
      Office_Corridor_L01 [packages/shared]
        Corridor_ceiling_void [packages/shared]
          pipe_clash_hard [packages/cooling]
          pipe_clash_near [packages/cooling]
          pipe_clash_tangent [packages/cooling]
```

This is level → space → nested space → element. The full traversal also visits
`L00_Ground` and `L02_Office`; the package filter shows only occupied branches.
In usdview's layer browser, mute `packages/cooling/cooling.usda`. The manifest's
`proofs.mute.rows` entry records **184 predicted and observed dangling port sites**,
**11,995 unchanged world transforms**, and zero composition errors. It also records
495 dependent analysis errors: 475 `PipeMissingAxis`, 11 `ComplianceStale`,
6 `ClashResultWithoutElements` and 3 `QuantityStale`. Those analyses retain opinions
whose inputs were removed; the diagnostics identify the dependencies to restore.
Unmute the delivery to restore the baseline. Open `views/mep.usda` for MEP or
`views/plan-A.usda` and `views/plan-B.usda` for the two programmes.

Use Form C to explore editable layers without plugins. Use Form A with the
IFC reader configured below to consume the delivered IFCs directly. Form B opens
alone in stock USD, with the same scene and animation baked into one file;
package muting and view selection use the layered Forms A and C.

## Deliveries and layer order

`packages/` contains `shared`, `site`, `arch`, `structure`, `cooling`,
`electrical`, `it`, `fitout` and `security`. Each directory contains its IFC,
USD root, semantic layer, geometry crate, README and local overlays.
The shared delivery alone defines the spatial structure. Other deliveries
overlay it and define their elements, catalog types, systems and ports.

The 32 IFC/USD files outside cooling are copied byte for byte. Cooling is an
unchanged-model Bonsai 0.8.5 export from Blender 5.1.2, with its USD twin regenerated
by the pinned converter. Its [comparison receipt](packages/cooling/bonsai-export.json)
checks all 16,163 IFC GlobalIds, 184 document references and 184 document associations,
plus classification, relationship targets, world transforms and 776 meshes with
shared space extents. Only the two declared controlled meshes are excluded.
They remain the pinned display fixtures in the regenerated twin.

Architecture's 167 elements are delivered by Revit 2027. Its IFC and three USD
files come unchanged from data-centre 0.6.0; the package README and manifest
retain the native producer and its identity/placement acceptance. CCTV and
Compliance join the issued plan's door identity and approach drivers to the
native referents by UUID in their own input overlays. Geometry stays native.

Copied source stamps retain their original production tag; cooling's stamps name
its producer, accepted IFC hash and generator source hash. `dc.manifest.json` remains
the unchanged upstream publication manifest. The suite manifest records the
accepted replacement separately under `bonsai`. Package READMEs show their census.

Strongest first, the roots compose presentation, analysis roots, then each
package's presentation, optional derived placement, catalog drivers and delivery.
Shared is last. Form A replaces each USD delivery with
`<discipline>.ifc:SDF_FORMAT_ARGS:spine=over&geometry=1`; shared uses ordinary
`shared.ifc`. All roots declare the union of 17 stock fallback types.

The IFC reader flattens each materialization. Package driver layers restore
catalog inheritance, and analysis inheritance overlays propagate introduced
type APIs to occurrences. This lets upper-layer type refinements reach both
forms. Bulk analysis geometry uses `.usdc` crates;
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
use the full publication's source hashes and counts, select
among multiple WC spaces, and exclude prototype-only spatial extents before
running Repeat's original reconstruction proof. The submodules are unchanged.
Repeat also keeps native stair replacements active when the comparison reports
a removal and addition at the same path; its complete subtree proof still runs.
Revit's exported `IsExternal` property is true for all three native wall types.
BuildUp selects recipes and facade visibility by the named native types while
preserving that delivered property. The recipe width and classification checks
still apply.

Each worker receives `AECO_STUDY_ROOT=/Studies/<library>` before importing its
hook. Released scoping helpers relocate committed exact results; the suite
relocates writable copies of legacy inputs and validates their relationships,
references, connections and metadata. Library tools resolve their study root
from persisted data; Form B retains the library root receipts when sublayers
are flattened away. The suite checker inspects every analysis layer, including
unused view layers, and every presentation layer for obsolete paths.

Exact material face subsets on `BrepArray` have no stock USD element domain;
the integration omits those material-only subsets, retaining the mesh twins'
appearance and the exact geometry. Empty material-binding opinions are omitted
and authored bindings declare `MaterialBindingAPI`. Equivalent world placement
changes refresh exact/twin correlation stamps without claiming new tessellation.

## Reproduce and verify

For computation, use the converter Python with USD 26.8, numpy, packaging,
IfcOpenShell, Pillow, PyYAML, Pydantic and the dependencies supplied by the pinned repositories.
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
env -u PYTHONPATH "$PYTHON" stage/build.py --flatten
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
Normal builds regenerate cooling's twin from the committed Bonsai IFC, rerun
the analysis hooks and flatten Form A. `--flatten` only rebuilds Form B from
the existing connected root, writing `out/demo-datacentre-01.flat.usdc` and
copying it into `stage/` when it is at most 10,000,000 bytes. Larger crates stay
in `out/`: attach that file to the matching release tag, together with the
manifest's byte count, SHA-256 and `sdf-usda-v1` normalized hash. Never commit it.

To repeat the producer transaction, set `AECO_BLENDER` to Blender 5.1.2 with
Bonsai 0.8.5, then run:

```sh
env -u PYTHONPATH "$PYTHON" tools/usdaeco_suite/bonsai_delivery.py
env -u PYTHONPATH "$PYTHON" stage/build.py
env -u PYTHONPATH "$PYTHON" stage/check.py --record
```

Each Blender run has a 900-second budget. The importer and exporter make no
model edits. Only the header filename and timestamp are normalized for repeatable
publication; the receipt retains the raw export hash. An unequal comparison
retains the generator delivery and records the differences. Rebuilds use the
accepted delivery as an input and do not require Blender.

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
| Root prims (A, B and C) | `demo_datacentre_01`, `Renders`, `Studies` |
| Catalog | `/demo_datacentre_01/_TypeCatalog` only |
| Outside-building analysis namespaces | Nine under `/Studies/<library>` |
| Connected and USD-only prims | 15,605 each; identical |
| Flattened scene / raw prims | 15,605 / 15,611 |
| Flattened crate bytes | 3,184,833; committed |
| Flattened normalized SHA-256 | `d6fbbe7199dd554b12946c6cf5f7a575e4e6e0f48d96937107cb42c59c0f6093` |
| Flattened generated prototype prims | 6 |
| Flattened deterministic builds | Three equal `sdf-usda-v1` hashes |
| Bonsai IFC GlobalIds / document links | 16,163 / 184; zero lost or changed |
| Compared meshes | 3,583; two declared exclusions |
| Plugin-free views | 21 |
| Registered validators executed | 124 |
| Unexpected integration errors | 0 |
| Expected findings (error severity) | 69 |
| Animated prims / transform samples | 19 / 109 |
| Mute cases / placement changes | 120 / 0 |
| Predicted and observed dangling port sites | 1,008 each |
| Stage gate | 12 checks, 0 failed |
| Text layers in the rebuild comparison | 180 |
| Source gate | 55 checks, 0 failed |
| Pytest | 53 passed |

The published analyses encode expected findings with validator error severity:
13 `MisplacedDevice` results from Compliance and 56 `RepeatDrift` results from
Repeat. Native door envelopes change the measured leaf-edge offsets; native
stair types and slab representations add comparison findings. These are
measured findings, with no count forced to match the generator-only stage.
`expectedFindings` names each rule, count, producing library and its
`integrated-findings.json`. The gate independently cross-checks those analysis
findings and requires the validator error multiset to match exactly. Any extra
error, including `ComplianceStale`, fails. The final full-plugin computation
has no stale compliance receipts; `integrationFindings` is empty.

The mute table covers 100 used layers (including 20 empty layers) and 20
view-only layers absent from the integrated stack. Sixty-one cases expose
additional analysis dependency errors.

Muting source or analysis dependencies can invalidate persisted derived receipts
and proxy links. The mute table retains those diagnostic counts separately from
composition, transform changes and the source manifest's predicted cross-package
port links. This is a deviation from the port-only diagnostic requirement; it does not
claim that a muted study remains current.

All delivered source stamps match their adjacent IFC bytes. The earlier
mismatches for electrical and IT are resolved by the pinned data release.
The content audit also checked 28 decoded geometry crates. The sanitizer recognizes only
canonical Revit type-property identifiers; their values and adjacent text
remain subject to every term and path check.

The exact producer hooks remain tied to their original native generation
recipes; their committed results are identified explicitly. Full-facility exact
recomputation is not proven. Nix packaging is not proven. The previous stage release
recorded one attempt that stopped at a public input lookup returning HTTP 404.
This lane uses existing runtime outputs and makes no new Nix attempt. The measured stock CPU
renderer uses USD 25.05.01; connected reads and strict checks use the supplied
USD 26.11 runtime, while plugin-free composition is also checked with USD 26.8.

Form B starts with `Usd.Stage.Flatten(addSourceFileComment=False)` of Form A.
The suite moves generated instance storage into its owning study, gives it
stable names derived from the source references, and retains library root
receipts alongside root metadata and provenance. USD introduces six generated
storage prims: the literal `TraverseAll` count is therefore 15,611 compared with
15,605 scene prims. This is a deviation from raw prim-count equality.
The checker reports those storage prims separately and compares every original
scene path, type, identity, world transform (including animation samples) and mesh.
`Flatten(C)` matches on those same fields; only the two declared mesh exclusions
apply. Sublayers, external references, payloads and asset-valued dependencies
are absent; internal instance references remain. The crate opens in a directory
containing no other files, with no suite plugins, using stock USD 26.8.
