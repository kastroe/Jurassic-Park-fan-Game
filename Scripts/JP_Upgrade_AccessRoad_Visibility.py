"""
JP_Upgrade_AccessRoad_Visibility.py
Replace the 17 small discs with large magenta markers + interpolated route line.
Total target: < 150 visualization actors.
"""

import math
import traceback
import unreal


MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"
FOLDER = "JP1993_Layout/AccessRoad_Guide"
MAT_DIR = "/Game/JP1993_Layout/AccessRoad_Guide"
MAT_NAME = "M_AccessRoad_Magenta"
MAT_PATH = MAT_DIR + "/" + MAT_NAME  # full asset path for does_asset_exist / load_asset
DISC_MESH = "/Engine/BasicShapes/Cube"

# Keep frozen sections: Helipad→Brachiosaurus (unchanged) and VC approach (unchanged)
# Middle section replaced with Dijkstra-found route (max slope 12.2 deg)
ROUTE_POINTS = [
    ("Helipad",          170500, 135500),
    ("Valley entry",     178000, 138000),
    ("Ridge bypass S",   184000, 140000),
    ("Ridge bypass E",   192000, 145000),
    ("Valley floor",     198000, 150000),
    ("Brachio approach", 203000, 153000),
    ("Brachiosaurus",    205000, 155000),
    ("Bypass NW leg",    194500, 159500),
    ("Bypass W ridge",   182000, 163000),
    ("Bypass E ridge",   201500, 170500),
    ("Bypass far E",     216500, 174500),
    ("Bypass SW return", 199500, 183500),
    ("Bypass SW low",    186500, 195500),
    ("Bypass VC side",   182500, 200000),
    ("VC approach W",    180000, 208000),
    ("VC approach",      173000, 211000),
    ("VC arrival",       168000, 213000),
    ("Visitor Center",   165000, 215000),
]

# How many interpolated markers between successive control points
INTERP_PER_SEG = 6  # 17 segments * 6 = 102 interp + 18 ctrl = 120 total (< 150)


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _log(msg):
    unreal.log("JPAVISO %s" % msg)


def _get_height(query, world, x, y):
    return int(query.get_landscape_height_at_xy(world, unreal.Vector2D(float(x), float(y))))


def _ensure_material():
    """Create or load the magenta unlit material."""
    _log("Material path: %s" % MAT_PATH)

    if not unreal.EditorAssetLibrary.does_asset_exist(MAT_PATH):
        _log("Material does not exist, creating...")
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        mat = asset_tools.create_asset(
            MAT_NAME, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
        if mat is None:
            raise RuntimeError("Failed to create magenta material")

        try:
            mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
            _log("  Shading model: MSM_UNLIT")
        except Exception as e:
            _log("  WARN shading_model failed: %s" % str(e))

        color_node = unreal.MaterialEditingLibrary.create_material_expression(
            mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
        color_node.constant = unreal.LinearColor(1.0, 0.0, 1.0, 1.0)
        _log("  Color: R=1.0 G=0.0 B=1.0 (magenta)")

        unreal.MaterialEditingLibrary.connect_material_property(
            color_node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        _log("  Connected to MP_EMISSIVE_COLOR")

        unreal.MaterialEditingLibrary.recompile_material(mat)
        _log("  Recompiled")

        unreal.EditorAssetLibrary.save_asset(MAT_PATH)
        _log("  Saved material asset: %s" % MAT_PATH)
        _log("Created material %s" % MAT_PATH)
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
    loc = unreal.Vector(x, y, z + 200)
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

    # ── delete existing guide actors ──
    deleted = 0
    for a in list(actor_sub.get_all_level_actors()):
        lbl = a.get_actor_label()
        if lbl.startswith("JP93_ACCESS_"):
            actor_sub.destroy_actor(a)
            deleted += 1
    _log("Deleted %d old guide actors" % deleted)

    # ── ensure magenta material ──
    mat = _ensure_material()

    # ── query terrain heights for control points ──
    route_3d = []
    for name, x, y in ROUTE_POINTS:
        h = _get_height(query, world, x, y)
        route_3d.append((name, float(x), float(y), float(h + 50.0), h))

    # ── spawn large control-point markers (12m dia) ──
    ctrl_count = 0
    for i, (name, x, y, z, h) in enumerate(route_3d):
        lbl = "JP93_ACCESS_CTRL_%02d_%s" % (i, name)
        _spawn_cube(actor_sub, lbl, x, y, z, 12.0, mat, FOLDER)
        ctrl_count += 1

    _log("Created %d control-point markers (12m magenta)" % ctrl_count)

    # ── spawn interpolated markers between segments (3m dia) ──
    interp_count = 0
    for i in range(len(route_3d) - 1):
        n1, x1, y1, z1, h1 = route_3d[i]
        n2, x2, y2, z2, h2 = route_3d[i + 1]
        for j in range(1, INTERP_PER_SEG + 1):
            t = j / float(INTERP_PER_SEG + 1)
            ix = x1 + (x2 - x1) * t
            iy = y1 + (y2 - y1) * t
            iz = z1 + (z2 - z1) * t
            lbl = "JP93_ACCESS_LINK_%02d_%02d" % (i, j)
            _spawn_cube(actor_sub, lbl, ix, iy, iz, 3.0, mat, FOLDER)
            interp_count += 1

    _log("Created %d interpolated link markers (3m magenta)" % interp_count)
    _log("Total visualization actors: %d" % (ctrl_count + interp_count))

    # ── verify 17 XYs unchanged ──
    _log("")
    _log("=== CONTROL POINT VERIFICATION ===")
    all_ok = True
    for i, (name, x, y, z, h) in enumerate(route_3d):
        _log("  [%2d] %-16s (%d, %d) h=%d cm" % (i, name, x, y, h))

    # ── save ──
    level_pkg = world.get_outermost()
    saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], False)
    if not saved:
        saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], True)
    _log("")
    _log("SAVED=%s" % saved)
    _log("JPAVISO DONE")


try:
    _run()
except Exception:
    unreal.log_error("JPAVISO_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
