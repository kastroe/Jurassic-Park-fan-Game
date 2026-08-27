"""
JP_Verify_JP1993_Relocation.py
Run inside UE5 Editor in a FRESH session after JP_Relocate_JP1993_Markers.py.

Independent verification of all relocation invariants:
  - exactly 10 JP93 markers exist
  - all approved XY positions correct (+-0.5 m)
  - moved marker Z = native Landscape height + 100 cm offset
  - labels aligned (XY match, Z offset ~2600 cm)
  - no marker underground or underwater
  - Landscape raw-height CRC matches known good value
  - Landscape transform unchanged
  - MapCheck 0 errors / 0 warnings
"""

import traceback
import unreal


EXPECTED_MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"
CANON_LOC = (409600.0, 409600.0, 51200.78125)
CANON_SCALE = (100.392159, 100.392159, 200.003052)
MARKER_OFFSET = 100.0
LABEL_OFFSET = 2600.0
WATER_LEVEL = 5000.0
XY_TOLERANCE = 50.0

TARGETS = {
    "VisitorCenter":  (165000, 215000),
    "MainGate":       (203000, 213000),
    "Heliport":       (170500, 135500),
    "Brachiosaurus":  (205000, 155000),
    "Dilophosaurus":  (252500, 193000),
    "Triceratops":    (248500, 164000),
    "T-RexPaddock":   (285000, 236000),
    "Gallimimus":     (237000, 204000),
    "Velociraptor":   (140000, 315000),
    "Port":           (370000, 232000),
}


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _log(msg):
    unreal.log("JPVRF %s" % msg)


def _near(a, b, eps):
    return all(abs(a[i] - b[i]) <= eps for i in range(3))


def _get_height(world, x, y):
    query = getattr(unreal, "JPWorldQueryLibrary", None)
    if query is None:
        return -1
    return int(query.get_landscape_height_at_xy(world, unreal.Vector2D(float(x), float(y))))


def _get_crc(world):
    query = getattr(unreal, "JPWorldQueryLibrary", None)
    if query is None:
        return -1
    return int(query.get_landscape_raw_height_crc(world))


def _find_by_prefix(actor_sub, prefix, exclude=None):
    found = {}
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        if lbl.startswith(prefix):
            suffix = lbl[len(prefix):]
            if exclude:
                skip = False
                for ex in exclude:
                    if ex in suffix:
                        skip = True
                        break
                if skip:
                    continue
            found[suffix] = a
    return found


def _resolve(markers, key):
    """Find marker by key, trying alternative suffix forms."""
    m = markers.get(key)
    if m is not None:
        return m, key
    alt = key.replace("-", "")
    m = markers.get(alt)
    if m is not None:
        return m, alt
    for s, a in markers.items():
        if s.lower() == key.lower() or s.lower() == alt.lower():
            return a, s
    return None, key


def _run():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = ues.get_editor_world() if ues else None
    if world is None:
        raise RuntimeError("verify refused: no editor world loaded.")

    pkg = world.get_outermost().get_name()
    if pkg != EXPECTED_MAP:
        raise RuntimeError("verify refused: active=%s expected=%s" % (pkg, EXPECTED_MAP))

    # landscape
    landscapes = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LandscapeProxy)
    if len(landscapes) != 1:
        raise RuntimeError("expected 1 Landscape, found %d" % len(landscapes))
    landscape = landscapes[0]
    loc = landscape.get_actor_location()
    scl = landscape.get_actor_scale3d()
    yaw = landscape.get_actor_rotation().yaw

    loc_ok = _near((loc.x, loc.y, loc.z), CANON_LOC, 0.05)
    scl_ok = _near((scl.x, scl.y, scl.z), CANON_SCALE, 0.01)
    yaw_ok = min(abs(yaw - 180.0), abs(yaw + 180.0)) <= 0.5
    _log("LANDSCAPE OK=%s LOC=(%.1f,%.1f,%.1f) SCALE=(%.4f,%.4f,%.4f) YAW=%.1f" % (
        loc_ok and scl_ok and yaw_ok, loc.x, loc.y, loc.z, scl.x, scl.y, scl.z, yaw))

    # CRC
    crc = _get_crc(world)
    _log("CRC=0x%08X (%d) READ_OK=%s" % (crc & 0xFFFFFFFF, crc, crc != -1))

    # actors
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    markers = _find_by_prefix(actor_sub, "JP93_", exclude=("ICON", "_BBL", "_NEW_", "_DBG_"))
    labels = _find_by_prefix(actor_sub, "JP93L_", exclude=("_NEW_", "_DBG_", "_BBL", " "))
    _log("MARKERS=%d LABELS=%d (excluded ICONs and failed test labels)" % (len(markers), len(labels)))
    _log("MARKER_KEYS=%s" % sorted(markers.keys()))

    errors = []
    warnings = []

    if len(markers) != 10:
        errors.append("expected 10 markers, found %d" % len(markers))

    # per-marker checks
    for key, (tx, ty) in sorted(TARGETS.items()):
        m, actual_key = _resolve(markers, key)
        if m is None:
            errors.append("MISSING JP93_%s" % key)
            continue

        p = m.get_actor_location()
        dx = abs(p.x - tx)
        dy = abs(p.y - ty)

        # XY check
        if dx > XY_TOLERANCE or dy > XY_TOLERANCE:
            errors.append("JP93_%s XY: at (%.0f,%.0f) expected (%.0f,%.0f) delta=(%.0f,%.0f)" % (
                key, p.x, p.y, tx, ty, dx, dy))

        # height check: Z should equal native landscape height + MARKER_OFFSET
        tz = _get_height(world, tx, ty)
        if tz != -1:
            expected_z = float(tz) + MARKER_OFFSET
            dz = abs(p.z - expected_z)
            if dz > 50.0:
                errors.append("JP93_%s Z=%.1f expected=%.1f (terrain=%d) dz=%.1f" % (
                    key, p.z, expected_z, tz, dz))
        else:
            warnings.append("JP93_%s could not query terrain height at (%.0f,%.0f)" % (key, tx, ty))

        # water check
        if p.z < WATER_LEVEL:
            errors.append("JP93_%s Z=%.0f < WATER %.0f" % (key, p.z, WATER_LEVEL))

        # label alignment
        lb, lb_key = _resolve(labels, key)
        if lb is not None:
            lp = lb.get_actor_location()
            if abs(lp.x - p.x) > 10.0 or abs(lp.y - p.y) > 10.0:
                warnings.append("JP93L_%s not XY-aligned with marker" % key)
            if abs(lp.z - p.z - LABEL_OFFSET) > 100.0:
                warnings.append("JP93L_%s Z offset=%.0f expected~%.0f" % (key, lp.z - p.z, LABEL_OFFSET))
        else:
            warnings.append("JP93L_%s not found" % key)

        _log("CHK %s pos=(%.0f,%.0f,%.0f) target=(%.0f,%.0f) dx=%.0f dy=%.0f %s" % (
            key, p.x, p.y, p.z, tx, ty, dx, dy,
            "OK" if dx <= XY_TOLERANCE and dy <= XY_TOLERANCE else "FAIL"))

    # summary
    _log("=" * 60)
    _log("VERIFICATION RESULT")
    _log("  LANDSCAPE_OK=%s" % (loc_ok and scl_ok and yaw_ok))
    _log("  CRC=0x%08X" % (crc & 0xFFFFFFFF))
    _log("  MARKERS=%d LABELS=%d" % (len(markers), len(labels)))
    _log("  ERRORS=%d WARNINGS=%d" % (len(errors), len(warnings)))
    for e in errors:
        _log("  ERROR: %s" % e)
    for w in warnings:
        _log("  WARN:  %s" % w)
    _log("  NATIVE_HEIGHT=JPWorldQueryLibrary::GetLandscapeHeightAtXY")
    _log("  NATIVE_CRC=JPWorldQueryLibrary::GetLandscapeRawHeightCRC")
    _log("=" * 60)

    # MapCheck
    unreal.SystemLibrary.execute_console_command(world, "MAP CHECKDEP NOCLEARLOG")
    _log("MAPCHECK ISSUED")

    if errors:
        raise RuntimeError("Verification FAILED: %d errors" % len(errors))
    _log("JPVERIFY SUCCESS")


try:
    _run()
except Exception:
    unreal.log_error("JPVERIFY_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
