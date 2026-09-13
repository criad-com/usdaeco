# cooling delivery

Producer: Bonsai 0.8.5 (Blender 5.1.2) export of the generator delivery.

Bonsai loaded the pinned generator IFC and saved it without model edits.
The export header timestamp is normalized to the generator timestamp.
The adjacent USD twin is regenerated with the pinned converter (`spine=over`).
The two declared `tessellationControlled` display meshes are retained from
the pinned publication; their IFC swept solids remain unchanged.

| Verified census | Count |
|---|---:|
| elements | 737 |
| meshes | 737 |
| ports | 1718 |
| spatial | 0 |
| systems | 3 |
| types | 22 |
| zones | 0 |

All 16,163 IFC GlobalIds, 184 document references and 184 document associations
survive. Description, Location, Identification, related objects and relationship
GlobalIds are compared with multiplicity. Classification, relationship targets,
world transforms and 776 meshes (including shared space extents) match.
Two controlled meshes are excluded from the export comparison.

The measured receipt is [bonsai-export.json](bonsai-export.json).
`presentation.usda`, `drivers.usda` and `derived.usda` remain independently mutable.
The shared delivery alone defines the spatial structure.
