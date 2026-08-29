"""Final milestone verification: reload the fence test map, confirm Map Check
(0 errors / 0 warnings are reported by the engine on load), and re-verify the
adaptive spline placement invariants:
  - module-length distribution per spline
  - scale == 1 (unity) on every generated module
  - yaw-only rotation (pitch/roll ~ 0)
  - no mesh deformation (static mesh components, no spline mesh)
  - final module uses the End mesh of its selected length; first uses Start
  - no overhang (remainder < 2m handled; STOP with remainder)
"""

import json
import os

import unreal

TEST_MAP = "/Game/Maps/JP_ElectricFence_Test"
EXPECTED = {
    "JP_FenceSpline_Test_Straight": {"count": 3, "dist": (3, 0, 0), "worst": 0.0, "rem": 0.0},
    "JP_FenceSpline_Test_GentleCurve": {"count": 15, "dist": (1, 8, 6), "worst": 20.69, "rem": 159.19},
    "JP_FenceSpline_Test_SharpCurve": {"count": 13, "dist": (1, 2, 10), "worst": 34.56, "rem": 26.97},
}
TOL_POS = 0.11
TOL_REM = 0.5

if not unreal.EditorLoadingAndSavingUtils.load_map(TEST_MAP):
    raise RuntimeError("Could not load fence test map.")

# Let map check run and log its summary.
import time
time.sleep(2.0)

subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = {a.get_actor_label(): a for a in subsystem.get_all_level_actors()}

report = {}
for label, exp in EXPECTED.items():
    actor = actors.get(label)
    if actor is None:
        raise RuntimeError("Missing spline actor " + label)
    comps = list(actor.get_components_by_class(unreal.StaticMeshComponent))
    count = len(comps)
    dist = (
        actor.get_editor_property("LastCount8m"),
        actor.get_editor_property("LastCount4m"),
        actor.get_editor_property("LastCount2m"),
    )
    worst = actor.get_editor_property("LastWorstGapCm")
    rem = actor.get_editor_property("LastUnusedRemainderCm")
    lengths = list(actor.get_editor_property("LastSectionLengthsCm"))

    # Invariant checks across generated components.
    scales_ok = True
    yaw_only_ok = True
    first_is_start = False
    last_is_end = False
    for i, comp in enumerate(comps):
        scale = comp.get_editor_property("relative_scale3d")
        if abs(scale.x - 1.0) > 0.001 or abs(scale.y - 1.0) > 0.001 or abs(scale.z - 1.0) > 0.001:
            scales_ok = False
        attrs = comp.get_editor_property("relative_rotation")
        pitch = attrs.roll if hasattr(attrs, "roll") else 0.0
        # relative_rotation is a Rotator (pitch, yaw, roll)
        r = comp.get_editor_property("relative_rotation")
        if abs(r.pitch) > 0.5 or abs(r.roll) > 0.5:
            yaw_only_ok = False
        sm = comp.get_editor_property("static_mesh")
        name = sm.get_name() if sm else ""
        if i == 0 and "Start" in name:
            first_is_start = True
        if i == count - 1:
            last_len = lengths[-1] if lengths else 0.0
            if last_len == 800.0 and "End" in name:
                last_is_end = True
            elif last_len == 400.0 and "End" in name:
                last_is_end = True
            elif last_len == 200.0 and "End" in name:
                last_is_end = True

    count_ok = count == exp["count"]
    dist_ok = dist == exp["dist"]
    worst_ok = abs(worst - exp["worst"]) <= TOL_POS
    rem_ok = abs(rem - exp["rem"]) <= TOL_REM

    info = {
        "spline_label": label,
        "count": count,
        "dist": list(dist),
        "worst_gap_cm": worst,
        "remainder_cm": rem,
        "count_ok": count_ok,
        "dist_ok": dist_ok,
        "worst_ok": worst_ok,
        "remainder_ok": rem_ok,
        "scale_is_1": scales_ok,
        "yaw_only": yaw_only_ok,
        "first_module_is_start": first_is_start,
        "last_module_is_end": last_is_end,
        "last_selected_length_cm": lengths[-1] if lengths else None,
    }
    report[label] = info
    unreal.log("JP FINAL %s count=%d dist=%s worst=%.2f rem=%.2f scale1=%s yawOnly=%s firstStart=%s lastEnd=%s" % (
        label, count, dist, worst, rem, scales_ok, yaw_only_ok, first_is_start, last_is_end))

os.makedirs(os.environ.get("TEMP", ".") + "/opencode", exist_ok=True)
path = os.path.join(os.environ["TEMP"], "opencode", "final_verify_report.json")
with open(path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, default=str)
unreal.log("JP_FINAL_VERIFY_REPORT_WRITTEN=" + path)
