# JP Asset Builder

Standalone Blender Python tooling for deterministic, original, game-ready asset generation and read-only existing-asset inspection. It does not connect to or modify Unreal maps, levels, Landscapes, splines, or game assets.

## Requirement

Blender is required. The tool was validated with Blender 5.2.1 LTS.

## Generate

From this directory, run:

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --python jp_asset_builder.py -- --preset electric_fence
```

Useful overrides:

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --python jp_asset_builder.py -- --preset electric_fence --section-length 8 --post-height 4.5 --wire-count 7 --output "SM_JP_ElectricFence_8m.glb"
```

Additional options are `--wire-radius`, `--include-start-post 0|1`, `--include-end-post 0|1`, `--warning-sign 0|1`, `--no-fbx`, and `--no-preview`. Defaults are maintained in `presets/electric_fence.json`.

For spline placement, use `--variant start`, `--variant middle`, or `--variant end`. Each variant keeps all wires spanning its full local X range, but only the Start/End variants include their respective endpoint post. Render the approved post rhythm with `--spline-set-preview`; it creates a non-exported 24 m Start+Middle+End preview and validation report.

## Inspect Existing Assets

Existing source assets are never overwritten. Inspect a supported `GLB`, `OBJ`, or `BLEND` file with:

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --python jp_asset_builder.py -- --inspect "C:\path\to\source.glb"
```

This writes a read-only analysis report to `output/`, including bounds, orientation, origins, material slots, mesh counts, polycount, transform state, and basic normals/zero-area-face checks. `source_assets_manifest.json` registers known source files and deliberately records unknown licensing as `UNKNOWN`.

## Outputs

Exports are written to `output/`: a mandatory GLB, an FBX when Blender's FBX exporter is available, an angled PNG preview, and a JSON validation report with bounds and polycount.

The section origin is at the start, ground level, and fence centerline: `(0, 0, 0)`. `+X` runs along the fence section, `Y` is lateral, and `+Z` is up. This makes sections suitable for later spline placement. `include_start_post` and `include_end_post` allow the importer or placement workflow to avoid intentional shared-post duplication at joins.

## Unreal Import Notes

Import the generated static mesh manually into the desired Unreal content location. Do not scale it by 100: the source geometry uses metres. Verify Unreal's import-unit settings and preserve the source pivot. This tool intentionally performs no Unreal import or map editing.

## Future Presets

Add a JSON preset under `presets/`, then add its deterministic mesh-construction branch in `jp_asset_builder.py`. Keep each preset original, parameter-driven, and independently validated.
