"""Import the six approved 4m/2m V2 short-module GLBs into the existing V2 folder
without overwriting the approved 8m assets. Idempotent: skips assets that already
exist, imports the missing ones, then verifies every imported mesh's Unreal bounds.
"""

import json
import os

import unreal

PROJECT_ROOT = r"C:\Users\KASTROE\Downloads\JurassicPark1993_FanGame_UE58"
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "Tools", "JP_Asset_Builder", "output")
DESTINATION = "/Game/JP1993/Environment/Fences/Test/V2"
TEMP_DIR = os.path.join(os.environ.get("TEMP", r"C:\Users\KASTROE\AppData\Local\Temp"), "opencode")

ASSETS = (
    ("SM_JP_ElectricFence_4m_Start_v2", "SM_JP_ElectricFence_4m_Start_v2.glb", 400.0),
    ("SM_JP_ElectricFence_4m_Middle_v2", "SM_JP_ElectricFence_4m_Middle_v2.glb", 400.0),
    ("SM_JP_ElectricFence_4m_End_v2", "SM_JP_ElectricFence_4m_End_v2.glb", 400.0),
    ("SM_JP_ElectricFence_2m_Start_v2", "SM_JP_ElectricFence_2m_Start_v2.glb", 200.0),
    ("SM_JP_ElectricFence_2m_Middle_v2", "SM_JP_ElectricFence_2m_Middle_v2.glb", 200.0),
    ("SM_JP_ElectricFence_2m_End_v2", "SM_JP_ElectricFence_2m_End_v2.glb", 200.0),
)

asset_library = unreal.EditorAssetLibrary
results = []
for asset_name, filename, expected_x_cm in ASSETS:
    expected_mesh = "%s/%s/StaticMeshes/%s" % (DESTINATION, asset_name, asset_name)
    imported = False
    if not asset_library.does_asset_exist(expected_mesh):
        source_path = os.path.join(OUTPUT_DIR, filename)
        if not os.path.isfile(source_path):
            raise RuntimeError("Missing approved short-module GLB: " + source_path)
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", source_path)
        task.set_editor_property("destination_path", DESTINATION)
        task.set_editor_property("destination_name", asset_name)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("save", True)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        imported = True

    mesh_path = expected_mesh
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    if mesh is None:
        raise RuntimeError("Could not load imported mesh: " + mesh_path)
    bounds = mesh.get_bounds()
    box_extent = bounds.box_extent
    origin = bounds.origin
    total_extent = [
        round(box_extent.x * 2.0, 4),
        round(box_extent.y * 2.0, 4),
        round(box_extent.z * 2.0, 4),
    ]
    results.append({
        "asset_name": asset_name,
        "mesh_path": mesh_path,
        "imported_this_run": imported,
        "expected_x_cm": expected_x_cm,
        "bounds_origin_xyz_cm": [round(origin.x, 4), round(origin.y, 4), round(origin.z, 4)],
        "total_extent_xyz_cm": total_extent,
        "x_matches_expected": abs(total_extent[0] - expected_x_cm) <= 1.0,
    })
    unreal.log("JP SHORT IMPORT OBJ: %s -> %s x=%.1fcm" % (asset_name, mesh_path, total_extent[0]))

for info in results:
    unreal.log("JP SHORT IMPORT SUM: %s extent=%s matches=%s" % (info["asset_name"], info["total_extent_xyz_cm"], info["x_matches_expected"]))

os.makedirs(TEMP_DIR, exist_ok=True)
result_path = os.path.join(TEMP_DIR, "short_module_import_report.json")
with open(result_path, "w", encoding="utf-8") as fh:
    json.dump({"imports": results, "destination": DESTINATION}, fh, indent=2, default=str)
unreal.log("JP_SHORT_IMPORT_REPORT_WRITTEN=" + result_path)
