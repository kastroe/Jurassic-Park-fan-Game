"""
JP_Create_Candidate_Overlay.py
Create Access Road CANDIDATE overlay using cyan markers.
Control markers (12m) + interpolated link markers (3m) along 24-point route.

NO editor quit. NO manual material step. Landscape CRC verified before/after.
Run inside Unreal Editor Python.
"""

import math
import traceback
import unreal


MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"
FOLDER = "JP1993_Layout/AccessRoad_Candidate"
MAT_DIR = "/Game/JP1993_Layout/AccessRoad_Candidate"
MAT_NAME = "M_AccessRoad_Candidate_Cyan"
MAT_PATH = MAT_DIR + "/" + MAT_NAME
DISC_MESH = "/Engine/BasicShapes/Cube"
EXPECTED_CRC = 0xFBAE9000
VISIBILITY_OFFSET_CM = 200.0

# 24-point simplified route (validated: max 14.4 deg, 0 >15, 0 water)
ROUTE_24 = [
    ("Brachiosaurus",    205000, 155000),
    ("West-southwest",   183000, 146500),
    ("Southwest",        176500, 145000),
    ("Far-west",         150000, 173500),
    ("West-climb",       147500, 175500),
    ("Southwest-low",    141000, 181000),
    ("South",            140500, 184000),
    ("Southeast-climb",  144000, 192500),
    ("East-climb",       145000, 192000),
    ("North-climb",      145000, 200000),
    ("NE-climb-1",       145500, 200500),
    ("NE-climb-2",       148500, 200500),
    ("NE-climb-3",       148000, 199500),
    ("NE-climb-4",       148500, 199500),
    ("NE-climb-5",       148000, 198500),
    ("NE-climb-6",       149000, 198500),
    ("NE-climb-7",       148500, 198000),
    ("NE-climb-8",       149500, 198000),
    ("NE-climb-9",       149000, 197500),
    ("NE-climb-10",      148500, 197500),
    ("East-approach",    151500, 197000),
    ("NE-approach",      158000, 202500),
    ("East-VC",          179000, 207500),
    ("VC-approach-W",    180000, 208000),
]

# Frozen JP1993 canonical markers: (exact_label, expected_x, expected_y)
CANONICAL_MARKERS = [
    ("JP93_VisitorCenter",  165000, 215000),
    ("JP93_MainGate",       203000, 213000),
    ("JP93_Heliport",       170500, 135500),
    ("JP93_Port",           370000, 232000),
    ("JP93_T-RexPaddock",   285000, 236000),
    ("JP93_Dilophosaurus",  252500, 193000),
    ("JP93_Brachiosaurus",  205000, 155000),
    ("JP93_Triceratops",    248500, 164000),
    ("JP93_Gallimimus",     237000, 204000),
    ("JP93_Velociraptor",   140000, 315000),
]

# Link spacing: ~15m between interpolated markers
LINK_SPACING_CM = 1500.0


def _log(msg):
    unreal.log("JPCANDIDATE %s" % msg)


def _get_crc(world):
    """Raw Landscape heightfield CRC via JPWorldQueryLibrary.GetLandscapeRawHeightCRC.
    Returns unsigned 32-bit int (normalized from int32)."""
    query = getattr(unreal, "JPWorldQueryLibrary", None)
    if query is None:
        return None
    return int(query.get_landscape_raw_height_crc(world)) & 0xFFFFFFFF


def _get_height(query, world, x, y):
    """Native Landscape height query at world XY."""
    return int(query.get_landscape_height_at_xy(world, unreal.Vector2D(float(x), float(y))))


def _ensure_material():
    """Create or load the cyan unlit material."""
    _log("Material path: %s" % MAT_PATH)

    if not unreal.EditorAssetLibrary.does_asset_exist(MAT_PATH):
        _log("Material does not exist, creating...")

        if not unreal.EditorAssetLibrary.does_asset_exist(MAT_DIR):
            unreal.EditorAssetLibrary.make_directory(MAT_DIR)
            _log("  Created directory: %s" % MAT_DIR)

        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        mat = asset_tools.create_asset(
            MAT_NAME, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
        if mat is None:
            raise RuntimeError("Failed to create cyan material")

        try:
            mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
            _log("  Shading model: MSM_UNLIT")
        except Exception as e:
            _log("  WARN shading_model failed: %s" % str(e))

        color_node = unreal.MaterialEditingLibrary.create_material_expression(
            mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
        color_node.constant = unreal.LinearColor(0.0, 0.9, 1.0, 1.0)
        _log("  Color: R=0.0 G=0.9 B=1.0 (cyan)")

        unreal.MaterialEditingLibrary.connect_material_property(
            color_node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        _log("  Connected to MP_EMISSIVE_COLOR")

        unreal.MaterialEditingLibrary.recompile_material(mat)
        _log("  Recompiled")

        unreal.EditorAssetLibrary.save_asset(MAT_PATH)
        _log("  Saved material asset: %s" % MAT_PATH)
    else:
        _log("Material %s already exists" % MAT_PATH)

    loaded = unreal.EditorAssetLibrary.load_asset(MAT_PATH)
    if loaded is None:
        raise RuntimeError("load_asset returned None for %s" % MAT_PATH)

    actual_type = type(loaded).__name__
    _log("Loaded material: %s (type=%s)" % (loaded.get_full_name(), actual_type))

    if not isinstance(loaded, unreal.Material):
        raise RuntimeError("Loaded asset is not a Material: %s (type=%s)" % (MAT_PATH, actual_type))

    return loaded


def _spawn_cube(actor_sub, label, x, y, z, scale_xy, mat, folder):
    loc = unreal.Vector(x, y, z)
    actor = actor_sub.spawn_actor_from_class(
        unreal.StaticMeshActor, loc, unreal.Rotator(0, 0, 0))
    if actor is None:
        _log("FAIL spawn %s" % label)
        return None
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    actor.set_actor_scale3d(unreal.Vector(scale_xy, scale_xy, 0.1))
    smc = actor.static_mesh_component
    mesh = unreal.EditorAssetLibrary.load_asset(DISC_MESH)
    if mesh is None:
        _log("FAIL load mesh for %s" % label)
        return actor
    smc.set_static_mesh(mesh)
    smc.set_material(0, mat)
    assigned = smc.get_material(0)
    if assigned is None or assigned.get_full_name() != mat.get_full_name():
        _log("FAIL mat on %s (got: %s)" % (label, assigned.get_full_name() if assigned else "None"))
    smc.set_mobility(unreal.ComponentMobility.STATIC)
    return actor


def _snapshot_magenta(actor_sub):
    """Snapshot all JP93_ACCESS_* actor labels before candidate creation."""
    labels = []
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        if lbl.startswith("JP93_ACCESS_"):
            labels.append(lbl)
    labels.sort()
    return labels


def _verify_magenta(actor_sub, before_labels):
    """Verify magenta guide is unchanged: same count and same label set."""
    after_labels = []
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        if lbl.startswith("JP93_ACCESS_"):
            after_labels.append(lbl)
    after_labels.sort()

    count_match = (len(before_labels) == len(after_labels))
    labels_match = (before_labels == after_labels)

    _log("Magenta actors before: %d" % len(before_labels))
    _log("Magenta actors after:  %d" % len(after_labels))
    _log("Count match: %s" % count_match)
    _log("Labels match: %s" % labels_match)

    if not count_match:
        _log("ERROR: magenta count changed! before=%d after=%d" % (
            len(before_labels), len(after_labels)))
        return False
    if not labels_match:
        missing = set(before_labels) - set(after_labels)
        added = set(after_labels) - set(before_labels)
        if missing:
            _log("ERROR: magenta labels missing: %s" % missing)
        if added:
            _log("ERROR: magenta labels added: %s" % added)
        return False

    _log("Magenta guide: UNCHANGED (all %d labels match)" % len(before_labels))
    return True


def _verify_canonical(actor_sub, query, world):
    """Verify all 10 frozen JP1993 canonical markers by exact label and XY."""
    _log("")
    _log("=== VERIFY CANONICAL MARKERS ===")
    all_ok = True
    for label, ex, ey in CANONICAL_MARKERS:
        found = False
        for a in actor_sub.get_all_level_actors():
            if a.get_actor_label() == label:
                loc = a.get_actor_location()
                ax = loc.x
                ay = loc.y
                dx = abs(ax - ex)
                dy = abs(ay - ey)
                ok = (dx <= 1.0 and dy <= 1.0)
                status = "OK" if ok else "MOVED"
                _log("  %s: %s actual=(%.1f, %.1f) expected=(%d, %d) delta=(%.1f, %.1f)" % (
                    label, status, ax, ay, ex, ey, dx, dy))
                if not ok:
                    all_ok = False
                found = True
                break
        if not found:
            _log("  %s: NOT FOUND" % label)
            all_ok = False
    return all_ok


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

    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    # ── CRC before ──────────────────────────────────────────────────────────
    crc_before = _get_crc(world)
    if crc_before is None:
        raise RuntimeError("JPWorldQueryLibrary unavailable")
    _log("CRC_BEFORE=0x%08X" % crc_before)
    if crc_before != EXPECTED_CRC:
        raise RuntimeError(
            "Landscape CRC mismatch before start! expected=0x%08X got=0x%08X" % (
                EXPECTED_CRC, crc_before))

    # ── snapshot magenta guide before ───────────────────────────────────────
    magenta_before = _snapshot_magenta(actor_sub)
    _log("Magenta snapshot: %d actors" % len(magenta_before))

    # ── delete existing candidate actors ────────────────────────────────────
    deleted = 0
    for a in list(actor_sub.get_all_level_actors()):
        lbl = a.get_actor_label()
        if lbl.startswith("JP93_CANDIDATE_"):
            actor_sub.destroy_actor(a)
            deleted += 1
    if deleted > 0:
        _log("Deleted %d old candidate actors" % deleted)

    # ── ensure cyan material ────────────────────────────────────────────────
    mat = _ensure_material()

    # ── query terrain heights for control points ────────────────────────────
    route_3d = []
    for name, x, y in ROUTE_24:
        h = _get_height(query, world, x, y)
        route_3d.append((name, float(x), float(y), float(h + VISIBILITY_OFFSET_CM), h))

    # ── log route stats ─────────────────────────────────────────────────────
    _log("")
    _log("=== CANDIDATE ROUTE ===")
    total_dist = 0.0
    max_slope = 0.0
    for i in range(len(route_3d)):
        name, x, y, z, h = route_3d[i]
        if i > 0:
            prev_name, px, py, pz, ph = route_3d[i - 1]
            d = math.sqrt((x - px)**2 + (y - py)**2)
            sl = math.degrees(math.atan2(abs(h - ph), d))
            total_dist += d
            max_slope = max(max_slope, sl)
            _log("  %s -> %s: %.0fm %.1fdeg" % (prev_name, name, d / 100, sl))
        else:
            _log("  START: %s h=%dcm" % (name, h))

    _log("Total: %.1fkm max_slope=%.1fdeg" % (total_dist / 10000, max_slope))

    # ── spawn control markers (12m) ─────────────────────────────────────────
    ctrl_count = 0
    for i, (name, x, y, z, h) in enumerate(route_3d):
        lbl = "JP93_CANDIDATE_CTRL_%02d_%s" % (i, name)
        _spawn_cube(actor_sub, lbl, x, y, z, 12.0, mat, FOLDER)
        ctrl_count += 1

    _log("Created %d control markers (12m cyan)" % ctrl_count)

    # ── spawn interpolated link markers (3m, ~15m spacing, terrain-following)
    interp_count = 0
    for i in range(len(route_3d) - 1):
        n1, x1, y1, z1, h1 = route_3d[i]
        n2, x2, y2, z2, h2 = route_3d[i + 1]
        d = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        n_links = max(1, int(d / LINK_SPACING_CM))
        for j in range(1, n_links + 1):
            t = j / float(n_links + 1)
            ix = x1 + (x2 - x1) * t
            iy = y1 + (y2 - y1) * t
            ih = _get_height(query, world, ix, iy)
            iz = float(ih + VISIBILITY_OFFSET_CM)
            lbl = "JP93_CANDIDATE_LINK_%02d_%02d" % (i, j)
            _spawn_cube(actor_sub, lbl, ix, iy, iz, 3.0, mat, FOLDER)
            interp_count += 1

    _log("Created %d link markers (3m cyan, terrain-following)" % interp_count)
    _log("Total candidate actors: %d" % (ctrl_count + interp_count))

    # ── CRC after ───────────────────────────────────────────────────────────
    crc_after = _get_crc(world)
    _log("")
    _log("CRC_AFTER=0x%08X" % crc_after)
    crc_match = (crc_before == crc_after)
    _log("CRC_MATCH=%s" % crc_match)
    if not crc_match:
        raise RuntimeError(
            "Landscape CRC changed! before=0x%08X after=0x%08X — DO NOT SAVE" % (
                crc_before, crc_after))

    # ── verify magenta guide unchanged ──────────────────────────────────────
    _log("")
    _log("=== VERIFY MAGENTA GUIDE ===")
    magenta_ok = _verify_magenta(actor_sub, magenta_before)
    if not magenta_ok:
        raise RuntimeError("Magenta guide changed — DO NOT SAVE")

    # ── verify canonical markers ────────────────────────────────────────────
    canonical_ok = _verify_canonical(actor_sub, query, world)
    if not canonical_ok:
        raise RuntimeError("Canonical marker mismatch — DO NOT SAVE")

    # ── save only after all checks pass ─────────────────────────────────────
    level_pkg = world.get_outermost()
    saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], False)
    if not saved:
        saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], True)
    _log("SAVED=%s" % saved)

    _log("")
    _log("=" * 60)
    _log("CANDIDATE OVERLAY COMPLETE")
    _log("Folder: %s" % FOLDER)
    _log("Material: %s (auto-created)" % MAT_PATH)
    _log("Control markers: %d" % ctrl_count)
    _log("Link markers: %d (terrain-following)" % interp_count)
    _log("Total: %d actors" % (ctrl_count + interp_count))
    _log("CRC: 0x%08X -> 0x%08X (MATCH=%s)" % (crc_before, crc_after, crc_match))
    _log("Landscape: UNCHANGED")
    _log("Magenta guide: UNCHANGED (%d actors, labels match)" % len(magenta_before))
    _log("Canonical markers: ALL 10 VERIFIED")
    _log("Editor: STAYING OPEN")
    _log("=" * 60)
    _log("JPCANDIDATE DONE")


try:
    _run()
except Exception:
    unreal.log_error("JPCANDIDATE_FAILED\n%s" % traceback.format_exc())
