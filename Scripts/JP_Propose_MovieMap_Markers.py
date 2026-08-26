import unreal


# NEW MOVIE-MAP PROPOSAL ONLY
# This script creates unsaved visual markers and does not move production actors
# or modify Landscape data.

DIAGNOSTIC_ONLY = True
OVERLAY_LABELS = ("JP_MovieMap_Reference", "REF_JP_MOVIE_MAP")
MARKER_PREFIX = "JP_MOVIE_PROPOSAL_"
VISITOR_CENTER_XY = (-8000.0, 0.0)
MAIN_GATE_XY = (-11500.0, -21000.0)
MAIN_GATE_MARKER_YAW = 0.0

EXPECTED_OVERLAY_LOCATION = (-19000.0, -20000.0, 21635.0)
EXPECTED_OVERLAY_ROTATIONS = (
    (180.0, 0.0, -270.0),
    (0.0, 90.0, 180.0),
)
EXPECTED_OVERLAY_SCALE = (-1.05, 1.05, 1.05)
TRANSFORM_TOLERANCE = 0.1


def close_enough(actual, expected):
    return all(abs(float(a) - float(e)) <= TRANSFORM_TOLERANCE for a, e in zip(actual, expected))


def vector_tuple(value):
    return value.x, value.y, value.z


def rotator_tuple(value):
    return value.pitch, value.yaw, value.roll


def find_overlay(actor_subsystem):
    matches = [
        actor for actor in actor_subsystem.get_all_level_actors()
        if actor.get_actor_label() in OVERLAY_LABELS
    ]
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one movie-map reference actor (%s); found %d." % (
            ", ".join(OVERLAY_LABELS), len(matches),
        ))
    overlay = matches[0]
    location = vector_tuple(overlay.get_actor_location())
    rotation = rotator_tuple(overlay.get_actor_rotation())
    scale = vector_tuple(overlay.get_actor_scale3d())
    if not close_enough(location, EXPECTED_OVERLAY_LOCATION):
        raise RuntimeError("REF_JP_MOVIE_MAP location is not locked: %s" % (location,))
    if not any(close_enough(rotation, expected) for expected in EXPECTED_OVERLAY_ROTATIONS):
        raise RuntimeError("REF_JP_MOVIE_MAP rotation is not locked: %s" % (rotation,))
    if not close_enough(scale, EXPECTED_OVERLAY_SCALE):
        raise RuntimeError("REF_JP_MOVIE_MAP scale is not locked: %s" % (scale,))
    unreal.log("JP MOVIE MAP OVERLAY VERIFIED: label=%s location=%s rotation=%s scale=%s" % (
        overlay.get_actor_label(), location, rotation, scale,
    ))
    return overlay


def find_landscape(actor_subsystem):
    actors = actor_subsystem.get_all_level_actors()
    for actor in actors:
        if isinstance(actor, unreal.Landscape):
            return actor, actors
    for actor in actors:
        if isinstance(actor, unreal.LandscapeProxy):
            try:
                landscape = actor.get_landscape_actor()
                if landscape:
                    return landscape, actors
            except Exception:
                pass
    raise RuntimeError("No live Landscape actor was found for marker Z sampling.")


def diagnostic_native_terrain(world, label, x, y):
    query_class = getattr(unreal, "JPWorldQueryLibrary", None)
    if query_class is None:
        unreal.log_warning("JP MOVIE MAP NATIVE TERRAIN: %s native class unavailable" % label)
        return
    query = getattr(query_class, "get_world_surface_z", None)
    if not callable(query):
        unreal.log_warning("JP MOVIE MAP NATIVE TERRAIN: %s native function unavailable" % label)
        return
    try:
        result = query(world, unreal.Vector2D(x, y), 150000.0, -150000.0)
        if isinstance(result, (tuple, list)):
            success = bool(result[0]) if len(result) > 0 else False
            terrain_z = float(result[1]) if len(result) > 1 else 0.0
        else:
            success = bool(result)
            terrain_z = 0.0
        unreal.log("JP MOVIE MAP NATIVE TERRAIN: %s XY=(%.0f,%.0f) terrain_z=%s success=%s" % (
            label, x, y, terrain_z, success,
        ))
    except Exception as error:
        unreal.log_warning("JP MOVIE MAP NATIVE TERRAIN: %s native call failed type=%s error=%s" % (
            label, type(error).__name__, error,
        ))


def destroy_old_proposals(actor_subsystem):
    for actor in actor_subsystem.get_all_level_actors():
        if actor.get_actor_label().startswith(MARKER_PREFIX):
            actor_subsystem.destroy_actor(actor)


def spawn_marker(actor_subsystem, label, x, y, terrain_z, yaw, scale):
    marker = actor_subsystem.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(x, y, terrain_z + scale.z * 50.0),
        unreal.Rotator(0.0, yaw, 0.0),
    )
    marker.set_actor_label(MARKER_PREFIX + label)
    cube = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube")
    if cube is None:
        actor_subsystem.destroy_actor(marker)
        raise RuntimeError("Engine cube mesh could not be loaded for temporary marker.")
    marker.static_mesh_component.set_static_mesh(cube)
    marker.set_actor_scale3d(scale)
    return marker


actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
overlay = find_overlay(actor_subsystem)
landscape, all_actors = find_landscape(actor_subsystem)
landscape_actors = [
    actor for actor in all_actors
    if isinstance(actor, (unreal.Landscape, unreal.LandscapeProxy))
]
ignored_actors = [actor for actor in all_actors if actor not in landscape_actors]
if DIAGNOSTIC_ONLY:
    world = unreal.EditorLevelLibrary.get_editor_world()
    diagnostic_native_terrain(world, "VisitorCenter", VISITOR_CENTER_XY[0], VISITOR_CENTER_XY[1])
    diagnostic_native_terrain(world, "MainGate", MAIN_GATE_XY[0], MAIN_GATE_XY[1])
    unreal.log("JP MOVIE MAP DIAGNOSTIC COMPLETE: native terrain queries only; no markers, actor changes, Landscape edits, or saves performed")
    raise SystemExit("JP MOVIE MAP DIAGNOSTIC ONLY")
destroy_old_proposals(actor_subsystem)

visitor_z = sample_landscape_z(VISITOR_CENTER_XY[0], VISITOR_CENTER_XY[1], ignored_actors)
gate_z = sample_landscape_z(MAIN_GATE_XY[0], MAIN_GATE_XY[1], ignored_actors)

created = []
try:
    visitor_marker = spawn_marker(
        actor_subsystem,
        "VisitorCenter",
        VISITOR_CENTER_XY[0],
        VISITOR_CENTER_XY[1],
        visitor_z,
        0.0,
        unreal.Vector(8.0, 8.0, 8.0),
    )
    created.append(visitor_marker)
    gate_marker = spawn_marker(
        actor_subsystem,
        "MainGate_TourRoadCandidate",
        MAIN_GATE_XY[0],
        MAIN_GATE_XY[1],
        gate_z,
        MAIN_GATE_MARKER_YAW,
        unreal.Vector(12.0, 4.0, 8.0),
    )
    created.append(gate_marker)
except Exception:
    for actor in created:
        actor_subsystem.destroy_actor(actor)
    raise

unreal.log("JP MOVIE MAP PROPOSAL MARKER: VisitorCenter x=%.1f y=%.1f terrain_z=%.1f marker_z=%.1f" % (
    VISITOR_CENTER_XY[0], VISITOR_CENTER_XY[1], visitor_z, visitor_z + 400.0,
))
unreal.log("JP MOVIE MAP PROPOSAL MARKER: MainGate x=%.1f y=%.1f terrain_z=%.1f marker_z=%.1f yaw=%.1f" % (
    MAIN_GATE_XY[0], MAIN_GATE_XY[1], gate_z, gate_z + 400.0, MAIN_GATE_MARKER_YAW,
))
unreal.log("JP MOVIE MAP PROPOSAL COMPLETE: unsaved markers only; no production actors or Landscape modified")
