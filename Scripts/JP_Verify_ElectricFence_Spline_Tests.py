"""Reload-only validation for the saved isolated electric-fence spline tests."""

import unreal


TEST_MAP = "/Game/Maps/JP_ElectricFence_Test"
EXPECTED_COUNTS = {
    "JP_FenceSpline_Test_Straight": 3,
    "JP_FenceSpline_Test_GentleCurve": 15,
    "JP_FenceSpline_Test_SharpCurve": 13,
}
EXPECTED_DIST = {
    "JP_FenceSpline_Test_Straight": (3, 0, 0),
    "JP_FenceSpline_Test_GentleCurve": (1, 8, 6),
    "JP_FenceSpline_Test_SharpCurve": (1, 2, 10),
}


if not unreal.EditorLoadingAndSavingUtils.load_map(TEST_MAP):
    raise RuntimeError("Could not reload the isolated fence spline test map.")
actors = list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
tests = {actor.get_actor_label(): actor for actor in actors if actor.get_actor_label() in EXPECTED_COUNTS}
if set(tests) != set(EXPECTED_COUNTS):
    raise RuntimeError("Saved spline test actor labels do not match the expected set.")
for label, expected_count in EXPECTED_COUNTS.items():
    actor = tests[label]
    components = list(actor.get_components_by_class(unreal.StaticMeshComponent))
    if len(components) != expected_count:
        raise RuntimeError("%s reloaded with %d modules, expected %d." % (label, len(components), expected_count))
    if any(component.get_attach_parent() is None for component in components):
        raise RuntimeError("%s contains an unattached generated module." % label)
    actual_dist = (
        actor.get_editor_property("LastCount8m"),
        actor.get_editor_property("LastCount4m"),
        actor.get_editor_property("LastCount2m"),
    )
    if actual_dist != EXPECTED_DIST[label]:
        raise RuntimeError("%s distribution %s != expected %s." % (label, actual_dist, EXPECTED_DIST[label]))
    unreal.log("JP VERIFY %s count=%d dist=(8m=%d,4m=%d,2m=%d) worstGap=%.2fcm remainder=%.2fcm" % (
        label, len(components), actual_dist[0], actual_dist[1], actual_dist[2],
        actor.get_editor_property("LastWorstGapCm"), actor.get_editor_property("LastUnusedRemainderCm")))
unreal.log("JP ELECTRIC FENCE SPLINE RELOAD VALIDATION COMPLETE")
