"""Point the three test electric-fence spline actors at the full 8m/4m/2m x
Start/Middle/End V2 mesh set, rebuild them with the adaptive rule, verify the
module-length distribution / worst gap / max adjacent yaw delta / remainder, and
save the map."""

import json
import os

import unreal

TEMP_DIR = os.path.join(os.environ.get("TEMP", r"C:\Users\KASTROE\AppData\Local\Temp"), "opencode")
TEST_MAP = "/Game/Maps/JP_ElectricFence_Test"
BASE = "/Game/JP1993/Environment/Fences/Test/V2"

MESH = {
    "8m_S": "%s/SM_JP_ElectricFence_8m_Start_v2/StaticMeshes/SM_JP_ElectricFence_8m_Start_v2" % BASE,
    "8m_M": "%s/SM_JP_ElectricFence_8m_Middle_v2/StaticMeshes/SM_JP_ElectricFence_8m_Middle_v2" % BASE,
    "8m_E": "%s/SM_JP_ElectricFence_8m_End_v2/StaticMeshes/SM_JP_ElectricFence_8m_End_v2" % BASE,
    "4m_S": "%s/SM_JP_ElectricFence_4m_Start_v2/StaticMeshes/SM_JP_ElectricFence_4m_Start_v2" % BASE,
    "4m_M": "%s/SM_JP_ElectricFence_4m_Middle_v2/StaticMeshes/SM_JP_ElectricFence_4m_Middle_v2" % BASE,
    "4m_E": "%s/SM_JP_ElectricFence_4m_End_v2/StaticMeshes/SM_JP_ElectricFence_4m_End_v2" % BASE,
    "2m_S": "%s/SM_JP_ElectricFence_2m_Start_v2/StaticMeshes/SM_JP_ElectricFence_2m_Start_v2" % BASE,
    "2m_M": "%s/SM_JP_ElectricFence_2m_Middle_v2/StaticMeshes/SM_JP_ElectricFence_2m_Middle_v2" % BASE,
    "2m_E": "%s/SM_JP_ElectricFence_2m_End_v2/StaticMeshes/SM_JP_ElectricFence_2m_End_v2" % BASE,
}

LABELS = ["JP_FenceSpline_Test_Straight", "JP_FenceSpline_Test_GentleCurve", "JP_FenceSpline_Test_SharpCurve"]

asset_library = unreal.EditorAssetLibrary
meshes = {}
for key, path in MESH.items():
    obj = asset_library.load_asset(path)
    if obj is None:
        raise RuntimeError("Mesh not found for key %s: %s" % (key, path))
    meshes[key] = obj
    unreal.log("JP SPLINE MESH LOADED %s" % path)

if not unreal.EditorLoadingAndSavingUtils.load_map(TEST_MAP):
    raise RuntimeError("Could not load test map.")
subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = {a.get_actor_label(): a for a in subsystem.get_all_level_actors()}

FIELD_MAP = [
    ("StartMesh", "8m_S"),
    ("MiddleMesh", "8m_M"),
    ("EndMesh", "8m_E"),
    ("StartMesh4m", "4m_S"),
    ("MiddleMesh4m", "4m_M"),
    ("EndMesh4m", "4m_E"),
    ("StartMesh2m", "2m_S"),
    ("MiddleMesh2m", "2m_M"),
    ("EndMesh2m", "2m_E"),
]

report = {}
for label in LABELS:
    actor = actors.get(label)
    if actor is None:
        raise RuntimeError("Missing test spline actor: " + label)
    for prop, mesh_key in FIELD_MAP:
        actor.set_editor_property(prop, meshes[mesh_key])
    unreal.log("JP SPLINE %s CONFIGURED" % label)

unreal.log("JP_SPLINE_ALL_CONFIGURED")

for label in LABELS:
    actor = actors[label]
    actor.rebuild_fence()
    unreal.log("JP SPLINE %s REBUILT" % label)

for label in LABELS:
    actor = actors[label]
    info = {
        "spline_length_cm": actor.get_editor_property("LastSplineLengthCm"),
        "section_count": actor.get_editor_property("LastSectionCount"),
        "count_8m": actor.get_editor_property("LastCount8m"),
        "count_4m": actor.get_editor_property("LastCount4m"),
        "count_2m": actor.get_editor_property("LastCount2m"),
        "unused_remainder_cm": actor.get_editor_property("LastUnusedRemainderCm"),
        "worst_gap_cm": actor.get_editor_property("LastWorstGapCm"),
        "yaws": list(actor.get_editor_property("LastSectionYaws")),
        "lengths": list(actor.get_editor_property("LastSectionLengthsCm")),
        "gaps": list(actor.get_editor_property("LastSectionGapsCm")),
    }
    yaws = info["yaws"]
    max_yaw_delta = 0.0
    for a, b in zip(yaws, yaws[1:]):
        delta = abs(((b - a + 180.0) % 360.0) - 180.0)
        max_yaw_delta = max(max_yaw_delta, delta)
    info["max_adjacent_yaw_delta_deg"] = max_yaw_delta
    report[label] = info
    unreal.log("JP SPLINE RESULT %s count=%d (8m=%d 4m=%d 2m=%d) worstGap=%.2fcm remainder=%.2fcm maxYawDelta=%.2f" % (
        label, info["section_count"], info["count_8m"], info["count_4m"], info["count_2m"],
        info["worst_gap_cm"], info["unused_remainder_cm"], info["max_adjacent_yaw_delta_deg"]))

# Save the map (save dirty packages; robust across engine APIs).
if hasattr(unreal.EditorLoadingAndSavingUtils, 'save_dirty_packages'):
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(save_map_packages=True, save_content_packages=False)
else:
    unreal.EditorLoadingAndSavingUtils.save_current_level()

os.makedirs(TEMP_DIR, exist_ok=True)
report_path = os.path.join(TEMP_DIR, "spline_test_report.json")
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, default=str)
unreal.log("JP_SPLINE_TEST_REPORT_WRITTEN=" + report_path)
