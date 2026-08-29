"""
JP_Verify_ConstructionMap.py  (step 2)
Runs with the construction map ALREADY OPEN (launch via -Map /Game/Maps/JP_JurassicDream_Construction).
Verifies the duplicated Landscape + retained frozen JP93 markers, then saves.

Read-only against the MASTER: we only inspect/save the construction world.
"""

import traceback
import unreal

CONSTRUCTION_PATH = "/Game/Maps/JP_JurassicDream_Construction"


def _log(m):
    unreal.log("JPVERIFY %s" % m)


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _gstr(g):
    try:
        return g.to_string()
    except Exception:
        return str(g)


def _run():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = ues.get_editor_world() if ues else None
    if world is None:
        raise RuntimeError("No editor world.")

    pkg = world.get_outermost().get_name()
    _log("ACTIVE_PACKAGE=%s" % pkg)
    if pkg != CONSTRUCTION_PATH:
        raise RuntimeError("Active package is %s, expected construction %s" % (pkg, CONSTRUCTION_PATH))

    proxies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LandscapeProxy)
    _log("LANDSCAPE_PROXY_COUNT=%d" % len(proxies))
    if len(proxies) == 1:
        proxy = proxies[0]
        loc = proxy.get_actor_location()
        scale = proxy.get_actor_scale3d()
        comps = proxy.get_components_by_class(unreal.LandscapeComponent)
        _log("PROXY_LABEL=%s" % proxy.get_actor_label())
        _log("PROXY_SCALE X=%.7f Y=%.7f Z=%.7f  ACTOR_Z=%.4f" % (scale.x, scale.y, scale.z, loc.z))
        _log("PROXY_COMPONENTS=%d" % len(comps))

    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    markers = [a for a in actor_sub.get_all_level_actors() if a.get_actor_label().startswith("JP93_")]
    _log("JP93_MARKER_COUNT=%d" % len(markers))
    key = ("T-RexPaddock", "VisitorCenter", "MainGate", "Dilophosaurus", "Triceratops", "Brachiosaurus", "Gallimimus")
    for a in markers:
        l = a.get_actor_label()
        if any(t in l for t in key):
            p = a.get_actor_location()
            _log("JP93 %s  X=%.1f Y=%.1f Z=%.1f" % (l, p.x, p.y, p.z))

    saved = unreal.EditorLoadingAndSavingUtils.save_current_level()
    if not saved:
        saved = unreal.EditorLoadingAndSavingUtils.save_packages([world.get_outermost()], True)
    _log("SAVED=%s" % saved)

    _log("VERIFY_DONE")


try:
    _run()
except Exception:
    unreal.log_error("JPVERIFY_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
