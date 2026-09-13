# Integrated stage — not built yet

This is the contract for a future integrated `demo-datacentre-01` stage.
**No roots, packages, analysis results, manifest, build tools or proofs below
have been built yet.** The current suite pins the existing separate examples.

The facility will be the `full` union of the base, floors, pod, clash and iris
fixtures: three storeys, pods and fix products, the planted pipes and security
readers. It will arrive as a shared spatial spine plus eight discipline packages:
architecture (`arch`), structure, cooling, electrical, IT (`it`), fitout, security
and site. The data repository's federated `dist/full` release and the IFC
repository's `usdIfc` reader are prerequisites; neither is in the current pins.

## Three forms

| Form | Planned root | Contract |
|---|---|---|
| A | `demo-datacentre-01.usda` | Connected: sublayers delivered IFC files directly through the `usdIfc` Sdf file-format plugin |
| B | `demo-datacentre-01.flat.usdc` | `Usd.Stage.Flatten` of A; self-contained, opens without plugins; manifest records its hash |
| C | `demo-datacentre-01.usd-only.usda` | The same layer stack over committed USD twins; composes without plugins, enriched by optional schema domains |

The IFC reader accepts `spine=over|def` (default `def`) and `geometry=0|1`.
Connected discipline inputs use `spine=over`; only the shared package defines
the spatial prims. A connected layer identifier will have the shape
`@packages/cooling/cooling.ifc:SDF_FORMAT_ARGS:spine=over@`.
Its twin is `packages/cooling/cooling.usda`, with semantic and geometry layers
beside it. Form C avoids external-source connections; all authored `Aeco*`
typed prims carry stock USD fallbacks. Form B resolves composition and assets.

## Planned layout

```text
stage/
  demo-datacentre-01.usda
  demo-datacentre-01.flat.usdc
  demo-datacentre-01.usd-only.usda
  packages/
    shared/                         shared.ifc + shared.usda + semantic/geometry layers
    arch/                           arch.ifc + arch.usda + semantic/geometry layers
    structure/                      structure.ifc + structure.usda + semantic/geometry layers
    cooling/                        cooling.ifc + cooling.usda + semantic/geometry layers
    electrical/                     electrical.ifc + electrical.usda + semantic/geometry layers
    it/                             it.ifc + it.usda + semantic/geometry layers
    fitout/                         fitout.ifc + fitout.usda + semantic/geometry layers
    security/                       security.ifc + security.usda + semantic/geometry layers
    site/                           site.ifc + site.usda + semantic/geometry layers
  analysis/
    cctv/                           kind, derived, studies, findings
    clash/                          results, exact-results
    plan/                           programme A and B, 4D, playback
    compliance/                     requirements and findings
    repeat/                         composition and quantities
    solid/                          exact bodies and display twins
  presentation/<library>.usda
  views/<view>.usda
  manifest.json
  build.py
  check.py
  README.md
```

Each package folder also has `README.md`, `drivers.usda`, `derived.usda` and
`presentation.usda`. Delivered files and twins are copied from `dist/full`
with source hashes recorded. The shared package alone defines project, site,
facility, levels, spaces and zones. Disciplines `over` that spine and define
only their own elements, types, systems and ports. Space extents are guides.

Every layer stamps `customLayerData` keys
`aeco:layer:{role,package,producer,source,sourceSha256,tag}`. Package READMEs
identify the producer. The generator supplies all packages first; subsequent
Revit or Bonsai IFC exports replace a delivery and its producer stamp without
changing how it composes. Live synchronization sessions remain in the integration
repositories' examples.

## Composition and ownership

From strongest to weakest, A and C stack presentation layers, analysis layers,
each discipline's presentation/derived/drivers/delivery layers, then the shared
package. A uses IFC deliveries; C substitutes their USD twins. Each discipline
and analysis has layers that can be muted independently and declares its ownership.
Muting a package or analysis must leave the remaining geometry's world
transforms unchanged. Cross-package port dependencies are named in the manifest.

There is one building namespace under `/demo_datacentre_01_Site`. Analyses have
their own roots outside the building. Systems and zones live under `/Systems`
and `/Zones`, with catalog classes under `/_TypeCatalog`. One `Usd.PrimRange`
traversal identifies spatial prims through `IsA(AecoSpatialBase)` and elements
through `HasAPI(AecoElementAPI)`. A future suite traversal utility reports level,
space, element and the package that owns the element's defining spec.

The root declares `defaultPrim = demo_datacentre_01`, metres, Z-up, the union of
all required `fallbackPrimTypes`, start time 0 and the union end time. Individual
4D views declare their own time ranges. Schema plugins register core first;
derived properties declare `aecoDerived = true` in schema definitions. Editors
write drivers; derivations author separate layers and mark derived gprims.

Analyses are recomputed on `full` using hooks from the pinned submodules.
Committed example results may be used only as a declared fallback with their
run/not-run status in the manifest. Presentation layers contain cameras,
visibility and display colour. Cameras move to `/Renders/<library>/<camera>`
to remove name collisions; presentation never changes building transforms.

## Views, manifest and reproduction

Small root layers select subsets of the same stack: `shell`, `architecture`,
`structure`, `mep`, `electrical`, `it`, `fitout`, `security`, `site`, `cctv`,
`clash`, `plan-A`, `plan-B`, `compliance`, `repeat`, `solid` and `all`.
Views use sublayer lists and documented muting, with no view variant set.

The manifest inventories every layer, role, package, producer, source hash,
counts, executed or unexecuted computation, release tag and cross-package port
link. The build reconstructs outputs from the pinned repositories. The suite
`build.sh` entry point will be extended to produce the flattened crate: commit it if it
is at most 10,000,000 bytes, otherwise publish a release asset. Record both its
file hash and deterministic `sdf-usda-v1` normalized hash. The federated source
publication has a separate 40 MB cap including delivered IFC files.

## Required proofs — all not run

1. Form C without plugins and A with only `usdIfc` have identical prim counts
   and world transforms. Relocation and stock rendering meet S27/S28.
2. A and C with all suite plugins run every registered validator: zero errors,
   with warnings recorded against the suite profile.
3. Muting each package and analysis in turn still composes, preserves every
   remaining world transform and introduces no validation error except named
   dangling cross-package port links already listed in the manifest.
4. B equals `Flatten(A)`, has a deterministic normalized hash, opens without
   plugins and obeys the crate size/publication rule.
5. Every layer has its required stamps; the manifest matches the tree; each
   IFC delivery read through `usdIfc` matches its USD twin's census and transforms.
6. Rebuilding from the recorded tags produces byte-identical text layers.

These are acceptance requirements, not evidence from version 0.1.0. The
[suite verification notes](../docs/verification.md) describe what is checked now.
