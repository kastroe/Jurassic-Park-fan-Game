"""
JP_Probe_VisitorCenter.py  (read-only)
Runs on the construction map (launch via -Map /Game/Maps/JP_JurassicDream_Construction).
Uses ONLY native read-only Landscape height queries (Landscape.GetHeightAtLocation).
No line traces. No sculpt/grade/move/save. Read-only probe for the VC pad proposal.

Frozen VC marker XY: (165000, 215000). Not moved.
"""

import traceback
import unreal

VC_X = 165000.0
VC_Y = 215000.0


def _log(m):
    unreal.log("JPVC %s" % m)


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _height(lscp, x, y):
    h = lscp.get_height_at_location(unreal.Vector(x, y, 0.0))
    if h is None:
        return None
    return float(h)


def _probe(landscape, cx, cy, half_x, half_y, step):
    # uniform grid over [cx-half_x, cx+half_x] x [cy-half_y, cy+half_y]
    vals = []
    x = cx - half_x
    while x <= cx + half_x + 0.001:
        y = cy - half_y
        while y <= cy + half_y + 0.001:
            h = _height(landscape, x, y)
            if h is not None:
                vals.append((x, y, h))
            y += step
        x += step
    return vals


def _stats(vals):
    if not vals:
        return None
    hs = [v[2] for v in vals]
    mn = min(hs); mx = max(hs); avg = sum(hs) / len(hs)
    return {"n": len(vals), "min": mn, "max": mx, "avg": avg}


def _run():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = ues.get_editor_world()
    pkg = world.get_outermost().get_name()
    _log("ACTIVE_PACKAGE=%s" % pkg)
    if pkg != "/Game/Maps/JP_JurassicDream_Construction":
        raise RuntimeError("Expected construction map, got %s" % pkg)

    proxies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LandscapeProxy)
    if len(proxies) != 1:
        raise RuntimeError("Expected 1 Landscape, found %d" % len(proxies))
    lscp = proxies[0]

    # VC marker height (read marker actor location then native height query at its XY)
    vc_h = _height(lscp, VC_X, VC_Y)
    _log("VC_MARKER_TERRAIN_HEIGHT X=%.1f Y=%.1f H=%.2f" % (VC_X, VC_Y, vc_h if vc_h is not None else -1.0))

    # Inner building pad: 60m x 50m -> half X 3000, half Y 2500
    pad = _probe(lscp, VC_X, VC_Y, 3000.0, 2500.0, 500.0)
    s_pad = _stats(pad)
    _log("REGION inner_pad bounds X[%.0f,%.0f] Y[%.0f,%.0f] %s" % (
        VC_X - 3000, VC_X + 3000, VC_Y - 2500, VC_Y + 2500, s_pad))

    # Apron/construction: 100m x 90m -> half X 5000, half Y 4500
    apron = _probe(lscp, VC_X, VC_Y, 5000.0, 4500.0, 1000.0)
    s_apron = _stats(apron)
    _log("REGION apron bounds X[%.0f,%.0f] Y[%.0f,%.0f] %s" % (
        VC_X - 5000, VC_X + 5000, VC_Y - 4500, VC_Y + 4500, s_apron))

    # Blend zone: +~25m around apron -> half X 7500, half Y 7000
    blend = _probe(lscp, VC_X, VC_Y, 7500.0, 7000.0, 1000.0)
    s_blend = _stats(blend)
    _log("REGION blend bounds X[%.0f,%.0f] Y[%.0f,%.0f] %s" % (
        VC_X - 7500, VC_X + 7500, VC_Y - 7000, VC_Y + 7000, s_blend))

    # Directional gradients: sample along 4 cardinal axes at blend radius vs center
    _log("DIRECTIONAL_GRADIENTS from VC center (H center=%.2f)" % (vc_h if vc_h is not None else -1.0))
    dirs = [("+X", 7000.0, 0.0), ("-X", -7000.0, 0.0), ("+Y", 0.0, 7000.0), ("-Y", 0.0, -7000.0)]
    for name, dx, dy in dirs:
        h = _height(lscp, VC_X + dx, VC_Y + dy)
        if h is not None and vc_h is not None:
            dist = (dx * dx + dy * dy) ** 0.5
            slope = abs(h - vc_h) / dist * 100.0 if dist > 0 else 0.0
            _log("DIR %s target(%.0f,%.0f) H=%.2f dH=%.2f slope=%.2f%% (%.2f deg)"
                 % (name, VC_X + dx, VC_Y + dy, h, h - vc_h, slope, _deg(h - vc_h, dist)))
        else:
            _log("DIR %s NO_HEIGHT" % name)

    _log("PROBE_DONE")


def _deg(dz, dist):
    if dist <= 0:
        return 0.0
    import math
    return math.degrees(math.atan(abs(dz) / dist))


try:
    _run()
except Exception:
    unreal.log_error("JPVC_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
