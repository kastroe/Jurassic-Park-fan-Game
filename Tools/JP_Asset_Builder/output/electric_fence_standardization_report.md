# Electric Fence Inspection And Standardization Report

## Source

- Source: `C:\Users\KASTROE\Downloads\obj\electric_fence_jurassic_park.glb`
- Source handling: read-only; it was not modified or copied.
- Licensing: creator and license are `UNKNOWN`; this source must not be redistributed unless its license is verified.
- Source preview: `electric_fence_jurassic_park_source_preview.png`

## Inspection

- Overall bounds: `19.602 x 1.710 x 7.601 m`.
- Bounds: X `-9.801` to `9.801`, Y `-0.500` to `1.210`, Z `-0.500` to `7.101 m`.
- Direction: the dominant axis is X. The assembly is centered near X=0 rather than starting at a ground-level endpoint.
- Objects/materials: 990 mesh objects, 990 material slots, and 11 named material assets.
- Polycount: 157,894 vertices and 172,542 faces.
- Mesh health: transforms are applied; the basic normals check found no invalid normals or zero-area faces.
- Wire construction: 11 full-length horizontal wire objects. Their center heights are approximately `0.813`, `1.399`, `1.973`, `2.558`, `3.197`, `3.792`, `4.442`, `5.037`, `5.580`, `6.165`, and `6.612 m`.
- Post construction: prominent structural posts occur around X=`-9.38`, `0`, and `9.39 m`; thinner intermediates occur near X=`-4.90` and `4.91 m`. Major-post mesh dimensions are approximately `0.191 x 0.393 x 6.714 m`.
- Insulators: detailed endpoint assemblies are present but fragmented across many unnamed mesh objects.
- Warning sign: none was discernible in the source preview or object metadata.

## Suitability Decision

The source is **not suitable for direct Unreal spline-repeat use**. It is a long, centered multi-bay assembly with a base below Z=0, non-endpoint pivot, mixed endpoint/intermediate post types, 990 separate meshes, and a very high polycount for a repeated fence module. Its approximate 4.5-4.9 m post intervals also do not form a clean, explicitly declared endpoint repeat contract. Placing copies at its 19.602 m bounding length would not reliably align the structural endpoint positions, and shared-post behavior is undefined.

No cleaned copy was made because this is not a simple pivot/material cleanup case, and the source license is unverified. Instead, its broad structural characteristics were treated only as visual reference and an original deterministic modular asset was generated.

## Generated Fallback

- GLB: `SM_JP_ElectricFence_8m.glb`
- Preview: `SM_JP_ElectricFence_8m_preview.png`
- Validation: `SM_JP_ElectricFence_8m_validation.json`
- Optional FBX: `SM_JP_ElectricFence_8m.fbx`
- Dimensions: `8.0 x 0.525 x 4.5 m`
- Origin: `(0, 0, 0)` at section start, ground, and centerline.
- Coordinate system: +X is fence direction, Y is lateral, +Z is up.
- Complexity: 488 vertices and 334 faces.
- Modular validation: exact X range `0` to `8`, bottom at Z=`0`, applied transforms, valid normals/vertices, and no zero-area faces.
