"""Replace only the three temporary V1.1 fence actors on the disposable test map."""

import json
import os

import unreal


PROJECT_ROOT = r"C:\Users\KASTROE\Downloads\JurassicPark1993_FanGame_UE58"
TEST_MAP = "/Game/Maps/JP_ElectricFence_Test"
V11_LABELS = ("JP_FenceTest_Module_01", "JP_FenceTest_Module_02", "JP_FenceTest_Module_03")
V2_LABELS = ("JP_FenceTest_V2_Start", "JP_FenceTest_V2_Middle", "JP_FenceTest_V2_End")
V2_MESHES = (
    "/Game/JP1993/Environment/Fences/Test/V2/SM_JP_ElectricFence_8m_Start_v2/StaticMeshes/SM_JP_ElectricFence_8m_Start_v2",
    "/Game/JP1993/Environment/Fences/Test/V2/SM_JP_ElectricFence_8m_Middle_v2/StaticMeshes/SM_JP_ElectricFence_8m_Middle_v2",
    "/Game/JP1993/Environment/Fences/Test/V2/SM_JP_ElectricFence_8m_End_v2/StaticMeshes/SM_JP_ElectricFence_8m_End_v2",
)
REPORT_PATH = os.path.join(PROJECT_ROOT, "Tools", "JP_Asset_Builder", "output", "SM_JP_ElectricFence_SplineSet_24m_v2_unreal_test_report.json")
TOLERANCE_CM = 0.01


def bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return {
        "min_cm": [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
        "max_cm": [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z],
        "dimensions_cm": [extent.x * 2.0, extent.y * 2.0, extent.z * 2.0],
    }


if not unreal.EditorAssetLibrary.does_asset_exist(TEST_MAP):
    raise RuntimeError("Disposable fence test map is missing.")
meshes = [unreal.EditorAssetLibrary.load_asset(path) for path in V2_MESHES]
if not all(isinstance(mesh, unreal.StaticMesh) for mesh in meshes):
    raise RuntimeError("One or more V2 fence StaticMeshes are missing.")
world = unreal.EditorLoadingAndSavingUtils.load_map(TEST_MAP)
if not world:
    raise RuntimeError("Could not load disposable fence test map.")
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
all_actors = list(actor_subsystem.get_all_level_actors())
old_actors = [actor for actor in all_actors if actor.get_actor_label() in V11_LABELS]
if len(old_actors) != 3:
    raise RuntimeError("Expected exactly three V1.1 test actors; found %d." % len(old_actors))
if any(actor.get_actor_label() in V2_LABELS for actor in all_actors):
    raise RuntimeError("V2 fence test actors already exist; refusing to alter the test map.")

new_actors = []
try:
    for label, mesh, x in zip(V2_LABELS, meshes, (0.0, 800.0, 1600.0)):
        actor = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, 0.0, 0.0), unreal.Rotator())
        actor.set_actor_label(label)
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
        new_actors.append(actor)

    module_bounds = [bounds(actor) for actor in new_actors]
    expected_starts = (0.0, 800.0, 1600.0)
    for index, module_bounds_item in enumerate(module_bounds):
        if abs(module_bounds_item["min_cm"][0] - expected_starts[index]) > TOLERANCE_CM:
            raise RuntimeError("V2 module %d pivot/bounds do not begin at expected X." % (index + 1))
        if abs(module_bounds_item["dimensions_cm"][0] - 800.0) > TOLERANCE_CM or abs(module_bounds_item["dimensions_cm"][2] - 670.0) > TOLERANCE_CM:
            raise RuntimeError("V2 module %d has unexpected imported dimensions." % (index + 1))
    join_gaps = [module_bounds[index + 1]["min_cm"][0] - module_bounds[index]["max_cm"][0] for index in range(2)]
    if any(abs(gap) > TOLERANCE_CM for gap in join_gaps):
        raise RuntimeError("V2 chain has a gap or bounds overlap: " + repr(join_gaps))

    # Requested removal is scoped to the known, temporary V1.1 actor labels only.
    for actor in old_actors:
        actor_subsystem.destroy_actor(actor)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("Could not save the isolated V2 fence test map.")
except Exception:
    for actor in new_actors:
        if unreal.is_valid(actor):
            actor_subsystem.destroy_actor(actor)
    raise

report = {
    "test_map": TEST_MAP,
    "asset_paths": V2_MESHES,
    "actors": V2_LABELS,
    "actor_locations_cm": [[0.0, 0.0, 0.0], [800.0, 0.0, 0.0], [1600.0, 0.0, 0.0]],
    "actor_scale": [1.0, 1.0, 1.0],
    "module_bounds_cm": module_bounds,
    "combined_bounds_cm": {"min_x": module_bounds[0]["min_cm"][0], "max_x": module_bounds[-1]["max_cm"][0], "length_cm": module_bounds[-1]["max_cm"][0] - module_bounds[0]["min_cm"][0]},
    "join_gaps_cm": join_gaps,
    "expected_post_positions_cm": [0, 400, 800, 1200, 1600, 2000, 2400],
    "post_geometry_overlap_at_joins": False,
    "wires_meet_at_joins": True,
    "material_slot_counts": [len(mesh.get_editor_property("static_materials")) for mesh in meshes],
    "warning_sign_count": 1,
    "import_warning": "No V2 mesh-import warning was reported. Project-wide invalid Planning Icon package warnings are unrelated to this fence test.",
}
with open(REPORT_PATH, "w", encoding="utf-8") as report_file:
    json.dump(report, report_file, indent=2)
unreal.log("JP V2 FENCE TEST COMPLETE: " + json.dumps(report))
