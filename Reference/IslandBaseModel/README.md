# JP Island Base Model

`SM_JP_Island_Base_2km.obj` is a new standalone terrain base modeled from the
supplied island map. It is not derived from any earlier project terrain.

## Dimensions

- North-south: 200,000 cm (2,000 m)
- Maximum east-west: 154,000 cm (1,540 m)
- Terrain relief: 0 to 18,000 cm (0 to 180 m)
- Below-water closed base: -2,500 cm (-25 m)
- Axes: Unreal-compatible centimeters, Z up, north at +Y

The mesh includes a broad central lowland for the park, mountain masses in the
northwest, west, northeast, east, and south, plus a closed coastline and sea
floor. It intentionally excludes buildings, roads, icons, labels, and map art.

## Generate

Run from the project root:

```powershell
py Reference/IslandBaseModel/Generate_JP_Island_Base_Model.py
```

## Unreal Import

1. In the Content Browser, create `/Game/JPImported/IslandBase`.
2. Import `SM_JP_Island_Base_2km.obj` into that folder.
3. Leave Import Uniform Scale at `1.0`; the mesh is already in centimeters.
4. Enable `Build Nanite` and `Generate Missing Collision`.
5. Use `Use Complex Collision As Simple` while blocking out, then replace it
   with custom collision before shipping if needed.

The terrain surface has roughly 20,000 quads, which keeps it suitable as a
base mesh for adding landscape details, roads, foliage, and park structures.
