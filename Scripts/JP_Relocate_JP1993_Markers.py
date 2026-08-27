"""
JP_Relocate_JP1993_Markers.py
Run inside UE5 Editor: -ExecutePythonScript="..."

Relocates all 10 JP93 macro-layout markers to approved brochure-terrain positions.
Landscape is READ-ONLY -- only marker/label actors are moved.

Height query path: JPWorldQueryLibrary.GetLandscapeHeightAtXY (native C++,
uses ALandscapeProxy::GetHeightAtLocation -- the same proven path used by
SnapTempMarkersToLandscape and ProbeJP1993Heights). No line traces.

CRC verification: JPWorldQueryLibrary.GetLandscapeRawHeightCRC reads the full
raw heightfield via FLandscapeEditDataInterface and computes FCrc::MemCrc32.
CRC is captured before relocation and verified after save to confirm the
Landscape is byte-identical.
"""

import traceback
import unreal


# ── CONFIG ──────────────────────────────────────────────────────────────────

EXPECTED_MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"

CANON_LOC = (409600.0, 409600.0, 51200.78125)
CANON_SCALE = (100.392159, 100.392159, 200.003052)

MARKER_HEIGHT_OFFSET = 100.0
LABEL_HEIGHT_OFFSET = 2600.0

# ── APPROVED MACRO LAYOUT (centimetres) ────────────────────────────────────

RELOCATIONS = [
    ("VisitorCenter",  "Visitor Center",  165000, 215000),
    ("MainGate",       "Main Gate",       203000, 213000),
    ("Heliport",       "Helipad",         170500, 135500),
    ("Brachiosaurus",  "Brachiosaurus",   205000, 155000),
    ("Dilophosaurus",  "Dilophosaurus",   252500, 193000),
    ("Triceratops",    "Triceratops",     248500, 164000),
    ("T-RexPaddock",   "T-Rex Paddock",   285000, 236000),
    ("Gallimimus",     "Gallimimus",      237000, 204000),
    ("Velociraptor",   "Velociraptor",    140000, 315000),
    ("Port",           "Port",            370000, 232000),
]


# ── HELPERS ─────────────────────────────────────────────────────────────────

def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _log(msg):
    unreal.log("JPRELOC %s" % msg)


def _near(a, b, eps):
    return all(abs(a[i] - b[i]) <= eps for i in range(3))


def _get_height(world, x, y):
    """Native landscape height query via JPWorldQueryLibrary.GetLandscapeHeightAtXY.
    Returns int32 height in cm (-1 on failure)."""
    query = getattr(unreal, "JPWorldQueryLibrary", None)
    if query is None:
        return -1
    return int(query.get_landscape_height_at_xy(world, unreal.Vector2D(float(x), float(y))))


def _get_crc(world):
    """Raw Landscape heightfield CRC via JPWorldQueryLibrary.GetLandscapeRawHeightCRC.
    Returns int32 CRC value (-1 on failure)."""
    query = getattr(unreal, "JPWorldQueryLibrary", None)
    if query is None:
        return -1
    return int(query.get_landscape_raw_height_crc(world))


def _find_by_prefix(actor_sub, prefix):
    found = {}
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        if lbl.startswith(prefix):
            found[lbl[len(prefix):]] = a
    return found


# ── MAIN ────────────────────────────────────────────────────────────────────

def _run():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = ues.get_editor_world() if ues else None
    if world is None:
        raise RuntimeError("relocate refused: no editor world loaded.")

    pkg = world.get_outermost().get_name()
    if pkg != EXPECTED_MAP:
        raise RuntimeError("relocate refused: active=%s expected=%s" % (pkg, EXPECTED_MAP))

    # ── landscape validation ────────────────────────────────────────────────
    landscapes = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LandscapeProxy)
    if len(landscapes) != 1:
        raise RuntimeError("relocate refused: expected 1 Landscape, found %d" % len(landscapes))
    landscape = landscapes[0]
    loc = landscape.get_actor_location()
    scl = landscape.get_actor_scale3d()
    yaw = landscape.get_actor_rotation().yaw

    if not _near((loc.x, loc.y, loc.z), CANON_LOC, 0.05):
        raise RuntimeError("landscape location mismatch")
    if not _near((scl.x, scl.y, scl.z), CANON_SCALE, 0.01):
        raise RuntimeError("landscape scale mismatch")
    if min(abs(yaw - 180.0), abs(yaw + 180.0)) > 0.5:
        raise RuntimeError("landscape yaw mismatch")

    _log("LANDSCAPE_OK LOC=(%.1f,%.1f,%.1f) SCALE=(%.4f,%.4f,%.4f) YAW=%.1f" % (
        loc.x, loc.y, loc.z, scl.x, scl.y, scl.z, yaw))

    # ── CRC before ──────────────────────────────────────────────────────────
    crc_before = _get_crc(world)
    if crc_before == -1:
        raise RuntimeError("failed to read Landscape raw-height CRC before relocation")
    _log("CRC_BEFORE=0x%08X (%d)" % (crc_before & 0xFFFFFFFF, crc_before))

    # ── find markers and labels ─────────────────────────────────────────────
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    markers = _find_by_prefix(actor_sub, "JP93_")
    labels = _find_by_prefix(actor_sub, "JP93L_")

    _log("FOUND MARKERS=%d LABELS=%d" % (len(markers), len(labels)))
    if len(markers) != 10:
        raise RuntimeError("expected 10 JP93_ markers, found %d" % len(markers))

    # ── record pre-change positions ─────────────────────────────────────────
    for sfx in sorted(markers):
        p = markers[sfx].get_actor_location()
        _log("PRE JP93_%s (%.0f, %.0f, %.0f)" % (sfx, p.x, p.y, p.z))

    # ── relocate each marker ────────────────────────────────────────────────
    moved = 0
    kept = 0
    errors = []
    results = []

    for sfx, display, nx, ny in RELOCATIONS:
        marker = markers.get(sfx)
        if marker is None:
            # try case-insensitive / alt suffix
            for s, a in markers.items():
                if s.lower() == sfx.lower() or s.lower() == sfx.replace("-", "").lower():
                    marker = a
                    sfx = s
                    break
        if marker is None:
            errors.append("MISSING JP93_%s" % sfx)
            continue

        label = labels.get(sfx)
        if label is None:
            for s, a in labels.items():
                if s.lower() == sfx.lower() or s.lower() == sfx.replace("-", "").lower():
                    label = a
                    break

        tz = _get_height(world, nx, ny)
        if tz == -1:
            errors.append("NO_HEIGHT %s at (%.0f,%.0f)" % (display, nx, ny))
            continue

        mz = float(tz) + MARKER_HEIGHT_OFFSET
        lz = mz + LABEL_HEIGHT_OFFSET

        old = marker.get_actor_location()
        dx = ((nx - old.x)**2 + (ny - old.y)**2)**0.5

        marker.set_actor_location(unreal.Vector(float(nx), float(ny), mz), False, False)
        if label is not None:
            label.set_actor_location(unreal.Vector(float(nx), float(ny), lz), False, False)

        action = "MOVED" if dx > 100.0 else "KEPT"
        if action == "MOVED":
            moved += 1
        else:
            kept += 1

        results.append({
            "name": display, "sfx": sfx,
            "old": (old.x, old.y, old.z),
            "new": (nx, ny, mz),
            "terrain": tz, "action": action, "dist_m": dx / 100.0,
        })

        _log("%s %s (%.0f,%.0f)->(%.0f,%.0f) TERRAIN=%.1f Z=%.1f d=%.1fm" % (
            action, display, old.x, old.y, nx, ny, tz, mz, dx / 100.0))

    if errors:
        for e in errors:
            _log("ERROR: %s" % e)
        raise RuntimeError("%d errors during relocation" % len(errors))

    # ── hide legacy tour road ───────────────────────────────────────────────
    hidden = 0
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        if lbl.startswith("TOUR_"):
            try:
                a.set_actor_hidden_in_game(True)
                a.set_is_temporarily_hidden_in_editor(True)
                root = a.get_root_component()
                if root is not None:
                    root.set_visibility(False, True)
                hidden += 1
            except Exception:
                pass
    _log("LEGACY_TOUR_ROAD HIDDEN=%d" % hidden)

    # ── save ────────────────────────────────────────────────────────────────
    level_pkg = world.get_outermost()
    saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], False)
    if not saved:
        saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], True)
    if not saved:
        raise RuntimeError("save failed")
    _log("SAVED=True")

    # ── CRC after ───────────────────────────────────────────────────────────
    crc_after = _get_crc(world)
    if crc_after == -1:
        raise RuntimeError("failed to read Landscape raw-height CRC after save")
    _log("CRC_AFTER=0x%08X (%d)" % (crc_after & 0xFFFFFFFF, crc_after))

    crc_match = (crc_before == crc_after)
    _log("CRC_MATCH=%s" % crc_match)
    if not crc_match:
        raise RuntimeError("Landscape CRC changed! before=0x%08X after=0x%08X" % (
            crc_before & 0xFFFFFFFF, crc_after & 0xFFFFFFFF))

    # ── post-change checks ─────────────────────────────────────────────────
    post_loc = landscape.get_actor_location()
    post_scl = landscape.get_actor_scale3d()
    loc_ok = _near((post_loc.x, post_loc.y, post_loc.z), CANON_LOC, 0.05)
    scl_ok = _near((post_scl.x, post_scl.y, post_scl.z), CANON_SCALE, 0.01)
    _log("LANDSCAPE_TRANSFORM_UNCHANGED=%s" % (loc_ok and scl_ok))

    post_m = _find_by_prefix(actor_sub, "JP93_")
    post_l = _find_by_prefix(actor_sub, "JP93L_")
    _log("POST_COUNT MARKERS=%d LABELS=%d" % (len(post_m), len(post_l)))
    if len(post_m) != 10:
        raise RuntimeError("marker count changed: %d" % len(post_m))

    # verify positions match approved targets
    pos_errs = []
    for sfx, display, ex, ey in RELOCATIONS:
        m = post_m.get(sfx)
        if m is None:
            pos_errs.append("MISSING JP93_%s" % sfx)
            continue
        p = m.get_actor_location()
        if abs(p.x - ex) > 50.0 or abs(p.y - ey) > 50.0:
            pos_errs.append("JP93_%s at (%.0f,%.0f) expected (%.0f,%.0f)" % (sfx, p.x, p.y, ex, ey))
    if pos_errs:
        for e in pos_errs:
            _log("POS_ERR: %s" % e)
        raise RuntimeError("position verification failed")

    # verify labels follow markers
    lbl_errs = []
    for sfx, display, ex, ey in RELOCATIONS:
        m = post_m.get(sfx)
        lb = post_l.get(sfx)
        if m is None or lb is None:
            continue
        mp = m.get_actor_location()
        lp = lb.get_actor_location()
        if abs(lp.x - mp.x) > 10.0 or abs(lp.y - mp.y) > 10.0:
            lbl_errs.append("JP93L_%s XY misaligned" % sfx)
        if abs(lp.z - mp.z - LABEL_HEIGHT_OFFSET) > 100.0:
            lbl_errs.append("JP93L_%s Z offset=%.0f expected~%.0f" % (sfx, lp.z - mp.z, LABEL_HEIGHT_OFFSET))
    if lbl_errs:
        for e in lbl_errs:
            _log("LBL_ERR: %s" % e)
        raise RuntimeError("label verification failed")

    # water check
    water_errs = []
    for sfx, display, ex, ey in RELOCATIONS:
        m = post_m.get(sfx)
        if m is None:
            continue
        p = m.get_actor_location()
        if p.z < 5000.0:
            water_errs.append("JP93_%s Z=%.0f < water 5000" % (sfx, p.z))
    if water_errs:
        for e in water_errs:
            _log("WATER_ERR: %s" % e)
        raise RuntimeError("markers below water")

    # MapCheck
    unreal.SystemLibrary.execute_console_command(world, "MAP CHECKDEP NOCLEARLOG")

    # ── summary ─────────────────────────────────────────────────────────────
    _log("=" * 60)
    _log("RELOCATION COMPLETE")
    _log("MOVED=%d KEPT=%d TOTAL=%d" % (moved, kept, moved + kept))
    _log("LEGACY_HIDDEN=%d" % hidden)
    _log("CRC_BEFORE=0x%08X CRC_AFTER=0x%08X MATCH=%s" % (
        crc_before & 0xFFFFFFFF, crc_after & 0xFFFFFFFF, crc_match))
    _log("NATIVE_HEIGHT_METHOD=JPWorldQueryLibrary::GetLandscapeHeightAtXY")
    _log("NATIVE_CRC_METHOD=JPWorldQueryLibrary::GetLandscapeRawHeightCRC")
    for r in results:
        _log("  %s %s: (%.0f,%.0f)->(%.0f,%.0f) T=%.1f Z=%.1f" % (
            r["action"], r["name"], r["old"][0], r["old"][1],
            r["new"][0], r["new"][1], r["terrain"], r["new"][2]))
    _log("=" * 60)
    _log("JPRELOC SUCCESS")


try:
    _run()
except Exception:
    unreal.log_error("JPRELOC_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
