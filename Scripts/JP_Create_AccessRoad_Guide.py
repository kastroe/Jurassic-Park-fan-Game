"""
JP_Create_AccessRoad_Guide.py
Create Access Road guide visualization using spaced marker discs.
No road mesh, no grading, no collision. Guide only.
"""

import math
import traceback
import unreal


MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"
FOLDER = "JP1993_Layout/AccessRoad_Guide"
DISC_MESH_PATH = "/Engine/BasicShapes/Cube"
WATER_LEVEL = 5000.0

# Route control points: (name, x, y)
ROUTE_POINTS = [
    ("Helipad",          170500, 135500),
    ("Valley entry",     178000, 138000),
    ("Ridge bypass S",   184000, 140000),
    ("Ridge bypass E",   192000, 145000),
    ("Valley floor",     198000, 150000),
    ("Brachio approach", 203000, 153000),
    ("Brachiosaurus",    205000, 155000),
    ("NW turn",          200000, 162000),
    ("Mountain base",    197000, 172000),
    ("Climb start",      195000, 182000),
    ("Saddle approach",  193500, 192000),
    ("Mountain pass",    192500, 197500),
    ("Descent end",      188000, 203000),
    ("VC approach W",    180000, 208000),
    ("VC approach",      173000, 211000),
    ("VC arrival",       168000, 213000),
    ("Visitor Center",   165000, 215000),
]


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _log(msg):
    unreal.log("JPACCESS %s" % msg)


def _get_height(query, world, x, y):
    return int(query.get_landscape_height_at_xy(world, unreal.Vector2D(float(x), float(y))))


def _slope_deg(h1, h2, dist):
    if dist <= 0:
        return 0.0
    return math.degrees(math.atan2(abs(h2 - h1), dist))


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

    # Delete existing guide if present
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        if lbl == "JP93_AccessRoad_Guide" or lbl.startswith("JP93_ACCESS_DISC_"):
            actor_sub.destroy_actor(a)
    _log("Cleaned up old guide actors")

    # Query terrain heights at all route points
    _log("Querying terrain heights...")
    route_3d = []
    for name, x, y in ROUTE_POINTS:
        h = _get_height(query, world, x, y)
        z = h + 50.0  # 50 cm above terrain
        route_3d.append((name, float(x), float(y), float(z), h))

    # Log route stats
    _log("")
    _log("=== ROUTE STATS ===")
    total_dist = 0.0
    max_slope = 0.0
    water_crossings = 0
    for i in range(len(route_3d)):
        name, x, y, z, h = route_3d[i]
        if h < WATER_LEVEL:
            water_crossings += 1
        if i > 0:
            prev_name, px, py, pz, ph = route_3d[i-1]
            dist = math.sqrt((x - px)**2 + (y - py)**2)
            slope = _slope_deg(ph, h, dist)
            total_dist += dist
            max_slope = max(max_slope, slope)
            _log("  %s -> %s: dist=%.0f m slope=%.1f deg" % (
                prev_name, name, dist/100.0, slope))
        else:
            _log("  START: %s h=%d cm" % (name, h))

    _log("")
    _log("Total route length: %.0f m" % (total_dist / 100.0))
    _log("Maximum slope: %.1f deg" % max_slope)
    _log("Water crossings: %d" % water_crossings)
    _log("Control points: %d" % len(route_3d))

    # Create visualization discs
    _log("")
    _log("Creating visualization discs...")
    disc_mesh = unreal.EditorAssetLibrary.load_asset(DISC_MESH_PATH)
    if disc_mesh is None:
        raise RuntimeError("Could not load Cube mesh")

    discs_created = 0
    for i, (name, x, y, z, h) in enumerate(route_3d):
        loc = unreal.Vector(x, y, z + 200)  # 2m above road surface
        disc = actor_sub.spawn_actor_from_class(
            unreal.StaticMeshActor, loc, unreal.Rotator(0, 0, 0))
        if disc is None:
            _log("  FAILED disc %d" % i)
            continue

        disc.set_actor_label("JP93_ACCESS_DISC_%02d_%s" % (i, name))
        disc.set_folder_path(FOLDER)
        disc.set_actor_scale3d(unreal.Vector(3.0, 3.0, 0.1))

        smc = disc.static_mesh_component
        smc.set_static_mesh(disc_mesh)
        smc.set_mobility(unreal.ComponentMobility.STATIC)
        discs_created += 1

    _log("Created %d visualization discs" % discs_created)

    # Save
    level_pkg = world.get_outermost()
    saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], False)
    if not saved:
        saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], True)
    _log("SAVED=%s" % saved)
    _log("JPACCESS DONE")


try:
    _run()
except Exception:
    unreal.log_error("JPACCESS_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
