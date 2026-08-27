"""
JP_Cleanup_Stray_Labels.py
Hide all non-canonical JP93L_* actors persistently.
Canonical labels are the 10 matching the approved marker names.
"""

import traceback
import unreal


MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"
CANONICAL_KEYS = {
    "VisitorCenter", "MainGate", "Heliport", "Port",
    "Brachiosaurus", "Triceratops", "Gallimimus",
    "T-RexPaddock", "Dilophosaurus", "Velociraptor",
}


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _log(msg):
    unreal.log("JPCLEAN %s" % msg)


def _run():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = ues.get_editor_world() if ues else None
    if world is None:
        raise RuntimeError("no editor world")

    pkg = world.get_outermost().get_name()
    if pkg != MAP:
        raise RuntimeError("wrong map: %s" % pkg)

    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    hidden = 0
    kept = 0
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        if not lbl.startswith("JP93L_"):
            continue

        suffix = lbl[len("JP93L_"):]
        is_canonical = suffix in CANONICAL_KEYS

        if is_canonical:
            kept += 1
            continue

        # Hide stray label
        a.set_actor_hidden_in_game(True)
        for c in a.get_components_by_class(unreal.PrimitiveComponent):
            c.set_editor_property("visible", False)
            c.set_editor_property("hidden_in_game", True)
        hidden += 1
        _log("HIDDEN: %s" % lbl)

    _log("Hidden %d stray labels, kept %d canonical" % (hidden, kept))

    level_pkg = world.get_outermost()
    saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], False)
    if not saved:
        saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], True)
    _log("SAVED=%s" % saved)
    _log("JPCLEAN DONE")


try:
    _run()
except Exception:
    unreal.log_error("JPCLEAN_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
