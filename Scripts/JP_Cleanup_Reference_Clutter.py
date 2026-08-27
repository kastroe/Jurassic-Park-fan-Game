"""
JP_Cleanup_Reference_Clutter.py
Hide old reference/clutter markers and enlarge JP93 labels for top-down readability.

Actions:
  1. Enlarge all JP93L_* labels to world_size=8000, rotate to face upward for top-down view
  2. Persistently hide MRK_*, MRKL_*, TEMP_Label_*, AUTO_JP_*, REF_* actors
  3. Persistently hide TEMP_WaterLevel_50m, TEMP_DirectionalLight, TEMP_SkyLight
  4. Save the map

Does NOT move JP93 markers. Does NOT create roads. Does NOT modify landscape.
"""

import traceback
import unreal


MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"
LABEL_WORLD_SIZE = 8000.0
# Rotation for top-down readability: Pitch=-90 makes forward point +Z (up)
# Text plane becomes horizontal, readable from above
LABEL_ROTATION = unreal.Rotator(pitch=-90.0, yaw=0.0, roll=0.0)

# Prefixes of old reference/clutter actors to hide
CLUTTER_PREFIXES = (
    "MRK_", "MRKL_", "TEMP_Label_",
    "AUTO_JP_", "REF_", "JP_MovieMap_Reference",
    "TEMP_WaterLevel", "TEMP_DirectionalLight", "TEMP_SkyLight",
)


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _log(msg):
    unreal.log("JPCLEAN %s" % msg)


def _hide_actor(a):
    """Persistently hide all primitive components of an actor."""
    comps = a.get_components_by_class(unreal.PrimitiveComponent)
    count = 0
    for c in comps:
        c.set_editor_property("visible", False)
        c.set_editor_property("hidden_in_game", True)
        count += 1
    a.set_actor_hidden_in_game(True)
    return count


def _run():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = ues.get_editor_world() if ues else None
    if world is None:
        raise RuntimeError("no editor world loaded")

    pkg = world.get_outermost().get_name()
    if pkg != MAP:
        raise RuntimeError("wrong map: %s" % pkg)

    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    # ── step 1: enlarge and reorient JP93L_* labels ───────────────────────
    labels = []
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        if lbl.startswith("JP93L_"):
            labels.append(a)

    _log("FOUND_LABELS=%d" % len(labels))
    enlarged = 0
    for a in labels:
        trc = a.get_component_by_class(unreal.TextRenderComponent)
        if trc is None:
            continue
        cur_size = trc.get_editor_property("world_size")
        if abs(cur_size - LABEL_WORLD_SIZE) > 10.0:
            trc.set_editor_property("world_size", LABEL_WORLD_SIZE)
            enlarged += 1
        # reorient for top-down: set actor rotation so text faces upward
        a.set_actor_rotation(LABEL_ROTATION, False)
        _log("LABEL %s size=%.0f rot=(%.0f,%.0f,%.0f)" % (
            a.get_actor_label(), LABEL_WORLD_SIZE,
            LABEL_ROTATION.pitch, LABEL_ROTATION.yaw, LABEL_ROTATION.roll))

    _log("LABELS_ENLARGED=%d" % enlarged)

    # ── step 2: hide clutter actors ────────────────────────────────────────
    clutter_hidden = 0
    clutter_components = 0
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        for prefix in CLUTTER_PREFIXES:
            if lbl.startswith(prefix):
                n = _hide_actor(a)
                clutter_components += n
                clutter_hidden += 1
                break

    _log("CLUTTER hidden actors=%d components=%d" % (clutter_hidden, clutter_components))

    # ── step 3: verify JP93 markers untouched ──────────────────────────────
    markers = []
    for a in actor_sub.get_all_level_actors():
        if a.get_actor_label().startswith("JP93_"):
            markers.append(a)
    _log("JP93_MARKERS=%d (must be 10)" % len(markers))
    if len(markers) != 10:
        raise RuntimeError("expected 10 JP93 markers, found %d" % len(markers))

    # ── save ───────────────────────────────────────────────────────────────
    level_pkg = world.get_outermost()
    saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], False)
    if not saved:
        saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], True)
    if not saved:
        raise RuntimeError("save failed")
    _log("SAVED=True")

    # ── summary ────────────────────────────────────────────────────────────
    _log("=" * 60)
    _log("REFERENCE CLEANUP COMPLETE")
    _log("  LABELS=%d ENLARGED=%d WORLD_SIZE=%.0f" % (len(labels), enlarged, LABEL_WORLD_SIZE))
    _log("  CLUTTER_HIDDEN=%d COMPONENTS=%d" % (clutter_hidden, clutter_components))
    _log("  JP93_MARKERS=%d" % len(markers))
    _log("=" * 60)
    _log("JPCLEAN SUCCESS")


try:
    _run()
except Exception:
    unreal.log_error("JPCLEAN_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
