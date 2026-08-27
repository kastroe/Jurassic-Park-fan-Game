"""
JP_Hide_TourRoad_Enlarge_Labels.py
Persistent visibility cleanup for obsolete TOUR_* road + label readability.

Actions:
  1. For every TOUR_* actor, set every PrimitiveComponent visible=False, hidden_in_game=True.
     These are serialized properties that survive editor reopen.
  2. Move all TOUR_* actors to JP1993_Layout/Legacy_OldTourRoad.
  3. Enlarge JP93L_* TextRenderComponent world_size for full-island top-view readability.
  4. Save the map.

Does NOT:
  - Move JP93 markers
  - Create roads
  - Modify landscape
  - Change approved macro layout
"""

import traceback
import unreal


MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"
LABEL_WORLD_SIZE = 4000.0
LEGACY_FOLDER = "/Game/Maps/JP_JurassicDream_Terrain_Test.JP1993_Layout/Legacy_OldTourRoad"


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _log(msg):
    unreal.log("JPHIDE %s" % msg)


def _run():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = ues.get_editor_world() if ues else None
    if world is None:
        raise RuntimeError("no editor world loaded")

    pkg = world.get_outermost().get_name()
    if pkg != MAP:
        raise RuntimeError("wrong map: %s" % pkg)

    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    # ── step 1: hide all TOUR_* primitive components persistently ──────────
    tour_actors = []
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        if lbl.startswith("TOUR_"):
            tour_actors.append(a)

    _log("FOUND_TOUR_ACTORS=%d" % len(tour_actors))

    components_hidden = 0
    for a in tour_actors:
        comps = a.get_components_by_class(unreal.PrimitiveComponent)
        for c in comps:
            c.set_editor_property("visible", False)
            c.set_editor_property("hidden_in_game", True)
            components_hidden += 1
        # also hide the actor itself
        a.set_actor_hidden_in_game(True)

    _log("COMPONENTS_HIDDEN=%d" % components_hidden)

    # ── step 2: move TOUR_* actors into legacy folder ──────────────────────
    folder_moved = 0
    for a in tour_actors:
        try:
            a.set_folder_path("JP1993_Layout/Legacy_OldTourRoad")
            folder_moved += 1
        except Exception:
            pass

    _log("FOLDER_MOVED=%d" % folder_moved)

    # ── step 3: enlarge JP93L_* labels for top-view readability ────────────
    labels = []
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        if lbl.startswith("JP93L_"):
            labels.append(a)

    _log("FOUND_LABELS=%d" % len(labels))

    labels_enlarged = 0
    for a in labels:
        trc = a.get_component_by_class(unreal.TextRenderComponent)
        if trc is not None:
            current_size = trc.get_editor_property("world_size")
            if abs(current_size - LABEL_WORLD_SIZE) > 10.0:
                trc.set_editor_property("world_size", LABEL_WORLD_SIZE)
                labels_enlarged += 1
                _log("ENLARGED %s world_size %.0f -> %.0f" % (
                    a.get_actor_label(), current_size, LABEL_WORLD_SIZE))
            else:
                _log("OK %s world_size=%.0f" % (a.get_actor_label(), current_size))

    _log("LABELS_ENLARGED=%d" % labels_enlarged)

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
    _log("HIDE_TOURROAD_LABELS COMPLETE")
    _log("  TOUR_ACTORS=%d COMPONENTS_HIDDEN=%d" % (len(tour_actors), components_hidden))
    _log("  FOLDER_MOVED=%d" % folder_moved)
    _log("  LABELS=%d ENLARGED=%d WORLD_SIZE=%.0f" % (len(labels), labels_enlarged, LABEL_WORLD_SIZE))
    _log("=" * 60)
    _log("JPHIDE SUCCESS")


try:
    _run()
except Exception:
    unreal.log_error("JPHIDE_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
