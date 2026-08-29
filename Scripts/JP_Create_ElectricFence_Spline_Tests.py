"""Create only the three approved electric-fence spline tests on the disposable map."""

import json
import math
import os

import unreal


PROJECT_ROOT = r"C:\Users\KASTROE\Downloads\JurassicPark1993_FanGame_UE58"
TEST_MAP = "/Game/Maps/JP_ElectricFence_Test"
REPORT_PATH = os.path.join(PROJECT_ROOT, "Tools", "JP_Asset_Builder", "output", "JP_ElectricFence_SplineTests_report.json")
V2_MESH_PATHS = (
    "/Game/JP1993/Environment/Fences/Test/V2/SM_JP_ElectricFence_8m_Start_v2/StaticMeshes/SM_JP_ElectricFence_8m_Start_v2",
    "/Game/JP1993/Environment/Fences/Test/V2/SM_JP_ElectricFence_8m_Middle_v2/StaticMeshes/SM_JP_ElectricFence_8m_Middle_v2",
    "/Game/JP1993/Environment/Fences/Test/V2/SM_JP_ElectricFence_8m_End_v2/StaticMeshes/SM_JP_ElectricFence_8m_End_v2",
)
OLD_V2_LABELS = ("JP_FenceTest_V2_Start", "JP_FenceTest_V2_Middle", "JP_FenceTest_V2_End")
TESTS = (
    ("JP_FenceSpline_Test_Straight", [(0, 0, 0), (2400, 0, 0)], unreal.SplinePointType.LINEAR),
    ("JP_FenceSpline_Test_GentleCurve", [(0, 4000, 0), (1500, 4000, 0), (3100, 4600, 0), (4500, 6200, 0)], unreal.SplinePointType.CURVE),
    ("JP_FenceSpline_Test_SharpCurve", [(0, 10000, 0), (800, 10000, 0), (1200, 10600, 0), (1200, 11800, 0), (600, 12400, 0)], unreal.SplinePointType.CURVE),
)
MODULE_LENGTH_CM = 800.0


def normalize_delta_degrees(current, previous):
    return (current - previous + 180.0) % 360.0 - 180.0


def spline_actor_report(actor, spline):
    static_components = list(actor.get_components_by_class(unreal.StaticMeshComponent))
    static_components.sort(key=lambda component: component.get_name())
    locations = []
    yaws = []
    for component in static_components:
        location = component.get_world_location()
        rotation = component.get_world_rotation()
        locations.append([location.x, location.y, location.z])
        yaws.append(rotation.yaw)
    yaw_deltas = [abs(normalize_delta_degrees(yaws[index], yaws[index - 1])) for index in range(1, len(yaws))]
    predicted_join_offsets = []
    for index in range(len(static_components) - 1):
        current_location = static_components[index].get_world_location()
        forward = static_components[index].get_forward_vector()
        expected_next = current_location + forward * MODULE_LENGTH_CM
        actual_next = static_components[index + 1].get_world_location()
        predicted_join_offsets.append((actual_next - expected_next).length())
    spline_length = spline.get_spline_length()
    section_count = int(math.floor(spline_length / MODULE_LENGTH_CM))
    return {
        "spline_length_cm": spline_length,
        "section_count": section_count,
        "start_count": 1 if section_count >= 2 else 0,
        "middle_count": max(section_count - 2, 0),
        "end_count": 1 if section_count >= 2 else 0,
        "unused_remainder_cm": spline_length - section_count * MODULE_LENGTH_CM,
        "generated_static_mesh_component_count": len(static_components),
        "section_world_positions_cm": locations,
        "section_yaws_degrees": yaws,
        "average_yaw_delta_degrees": sum(yaw_deltas) / len(yaw_deltas) if yaw_deltas else 0.0,
        "max_yaw_delta_degrees": max(yaw_deltas) if yaw_deltas else 0.0,
        "predicted_rigid_join_offsets_cm": predicted_join_offsets,
        "gaps_over_5cm": [offset for offset in predicted_join_offsets if offset > 5.0],
        "angular_quality": "unacceptable" if any(delta > 20.0 for delta in yaw_deltas) else "potentially_ugly" if any(delta > 15.0 for delta in yaw_deltas) else "noticeable" if any(delta > 10.0 for delta in yaw_deltas) else "acceptable",
    }


if not unreal.EditorAssetLibrary.does_asset_exist(TEST_MAP):
    raise RuntimeError("Disposable fence test map is missing.")
fence_class = unreal.load_class(None, "/Script/JurassicPark1993.JP_ElectricFenceSpline")
if not fence_class:
    raise RuntimeError("JPElectricFenceSpline class is unavailable; compile the project before running this script.")
meshes = [unreal.EditorAssetLibrary.load_asset(path) for path in V2_MESH_PATHS]
if not all(isinstance(mesh, unreal.StaticMesh) for mesh in meshes):
    raise RuntimeError("One or more approved V2 fence meshes are missing.")

world = unreal.EditorLoadingAndSavingUtils.load_map(TEST_MAP)
if not world:
    raise RuntimeError("Could not load disposable fence test map.")
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
all_actors = list(actor_subsystem.get_all_level_actors())
existing_tests = [actor for actor in all_actors if actor.get_actor_label().startswith("JP_FenceSpline_Test_")]
expected_test_labels = {test[0] for test in TESTS}
if existing_tests:
    if {actor.get_actor_label() for actor in existing_tests} != expected_test_labels:
        raise RuntimeError("Unexpected spline-test actors exist; refusing to modify them.")
    # Replace only the complete set created by this script after an actor implementation change.
    for actor in existing_tests:
        actor_subsystem.destroy_actor(actor)
    all_actors = list(actor_subsystem.get_all_level_actors())
old_v2_actors = [actor for actor in all_actors if actor.get_actor_label() in OLD_V2_LABELS]
if old_v2_actors and len(old_v2_actors) != 3:
    raise RuntimeError("Expected exactly three temporary V2 actors; found %d." % len(old_v2_actors))

created = []
try:
    for label, points, point_type in TESTS:
        actor = actor_subsystem.spawn_actor_from_class(fence_class, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator())
        actor.set_actor_label(label)
        actor.set_editor_property("start_mesh", meshes[0])
        actor.set_editor_property("middle_mesh", meshes[1])
        actor.set_editor_property("end_mesh", meshes[2])
        spline = actor.get_component_by_class(unreal.SplineComponent)
        spline.clear_spline_points(False)
        for point in points:
            spline.add_spline_point(unreal.Vector(*point), unreal.SplineCoordinateSpace.WORLD, False)
        for point_index in range(len(points)):
            spline.set_spline_point_type(point_index, point_type, False)
        spline.set_closed_loop(False, False)
        spline.update_spline()
        actor.call_method("RebuildFence", ())
        created.append((actor, spline))

    reports = {actor.get_actor_label(): spline_actor_report(actor, spline) for actor, spline in created}
    straight = reports["JP_FenceSpline_Test_Straight"]
    if straight["section_count"] != 3 or straight["generated_static_mesh_component_count"] != 3:
        raise RuntimeError("Straight test did not generate exactly Start + Middle + End.")
    if abs(straight["spline_length_cm"] - 2400.0) > 0.01 or straight["unused_remainder_cm"] > 0.01:
        raise RuntimeError("Straight test length/remainder is incorrect.")
    if straight["gaps_over_5cm"]:
        raise RuntimeError("Straight test has rigid join gaps over 5 cm.")

    # Remove only the prior, explicitly named temporary V2 actors after all tests validate.
    for actor in old_v2_actors:
        actor_subsystem.destroy_actor(actor)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("Could not save the isolated fence spline test map.")
except Exception:
    for actor, _ in created:
        if unreal.is_valid(actor):
            actor_subsystem.destroy_actor(actor)
    raise

report = {
    "test_map": TEST_MAP,
    "actor_class": "JP_ElectricFenceSpline",
    "module_length_cm": MODULE_LENGTH_CM,
    "tests": reports,
    "straight_expected_post_positions_cm": [0, 400, 800, 1200, 1600, 2000, 2400],
    "post_duplication": False,
    "material_slot_counts": {"start": len(meshes[0].get_editor_property("static_materials")), "middle": len(meshes[1].get_editor_property("static_materials")), "end": len(meshes[2].get_editor_property("static_materials"))},
    "warnings": "No spline mesh deformation is used. Rigid curve join offsets and yaw deltas are reported for human review.",
}
with open(REPORT_PATH, "w", encoding="utf-8") as report_file:
    json.dump(report, report_file, indent=2)
unreal.log("JP ELECTRIC FENCE SPLINE TESTS COMPLETE: " + json.dumps(report))
