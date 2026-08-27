"""
JP_Diag_Port_Shoreline.py
Query terrain height at Port position only.
"""

import traceback
import unreal


MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"
PORT_X = 370000.0
PORT_Y = 232000.0
WATER_LEVEL = 5000.0


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _log(msg):
    unreal.log("JPSHORE %s" % msg)


def _run():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = ues.get_editor_world() if ues else None
    if world is None:
        raise RuntimeError("no editor world")

    pkg = world.get_outermost().get_name()
    if pkg != MAP:
        raise RuntimeError("wrong map: %s" % pkg)

    query = getattr(unreal, "JPWorldQueryLibrary", None)
    if query is None:
        raise RuntimeError("JPWorldQueryLibrary not available")

    height = int(query.get_landscape_height_at_xy(world, unreal.Vector2D(PORT_X, PORT_Y)))
    _log("PORT position: (%.0f, %.0f)" % (PORT_X, PORT_Y))
    _log("TERRAIN_HEIGHT=%d cm (%.1f m)" % (height, height / 100.0))
    _log("WATER_LEVEL=%d cm (%.1f m)" % (WATER_LEVEL, WATER_LEVEL / 100.0))
    clearance = height - WATER_LEVEL
    _log("CLEARANCE=%d cm (%.1f m) %s water" % (clearance, clearance / 100.0, "ABOVE" if clearance >= 0 else "BELOW"))

    if clearance < 0:
        _log("STATUS: UNDERWATER")
    elif clearance < 200:
        _log("STATUS: AT SHORELINE (low ground near water)")
    else:
        _log("STATUS: INLAND (above water, ground elevation present)")

    _log("JPSHORE DONE")


try:
    _run()
except Exception:
    unreal.log_error("JPSHORE_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
