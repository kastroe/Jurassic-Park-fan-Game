"""Import only the approved V2 fence GLBs into a new, non-overwriting path."""

import os

import unreal


PROJECT_ROOT = r"C:\Users\KASTROE\Downloads\JurassicPark1993_FanGame_UE58"
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "Tools", "JP_Asset_Builder", "output")
DESTINATION = "/Game/JP1993/Environment/Fences/Test/V2"
ASSETS = (
    ("SM_JP_ElectricFence_8m_Start_v2", "SM_JP_ElectricFence_8m_Start_v2.glb"),
    ("SM_JP_ElectricFence_8m_Middle_v2", "SM_JP_ElectricFence_8m_Middle_v2.glb"),
    ("SM_JP_ElectricFence_8m_End_v2", "SM_JP_ElectricFence_8m_End_v2.glb"),
)


asset_library = unreal.EditorAssetLibrary
if asset_library.does_directory_exist(DESTINATION):
    raise RuntimeError("Refusing to import into existing V2 destination: " + DESTINATION)

tasks = []
for asset_name, filename in ASSETS:
    source_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(source_path):
        raise RuntimeError("Missing approved V2 GLB: " + source_path)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", source_path)
    task.set_editor_property("destination_path", DESTINATION)
    task.set_editor_property("destination_name", asset_name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("save", True)
    tasks.append(task)

unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
unreal.log("JP V2 FENCE IMPORT COMPLETE: imported three new GLBs into " + DESTINATION)
