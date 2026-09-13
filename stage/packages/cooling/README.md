# cooling delivery

Producer: {'version': '0.5.1'}. Source release: `v0.5.1`.

The IFC delivery and its USD twin are copied without changing their bytes.
The source layer stamps retain their original production tag; the suite manifest
records the release that supplied these bytes.

| Census | Count |
|---|---:|
| elements | 737 |
| meshes | 737 |
| ports | 1718 |
| spatial | 0 |
| systems | 3 |
| types | 22 |
| zones | 0 |

`presentation.usda` contains local display opinions and may be muted separately.
The shared delivery defines the spatial structure; other deliveries overlay it.

Two meshes are `tessellationControlled`: the near and tangent clash pipes.
Their IFC swept solids can tessellate differently from the controlled USD twins.
See `tessellationControlled` in the adjacent delivery manifest.
