import unreal


# BUILD 1.6 - IMPORTED VISITOR CENTER PLACEMENT
#
# Run after importing the Sketchfab GLB into /Game/JPImported/VisitorCenter.
# The imported mesh is the visual source of truth. B13, B15, and B10 are
# spatial/reference layers only and are never changed by this script.

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assetlib = unreal.EditorAssetLibrary

IMPORT_ROOT = "/Game/JPImported/VisitorCenter"
B13_PREFIX = "B13_JP_VC_"
B15_PREFIX = "B15_JP_VC_"
B10_GATE_PREFIX = "B10_JP_GATE_"
B10_PREFIX = "B10_"
B16_PREFIX = "B16_JP_VC_"
STAGING_PREFIX = "B16_JP_VC_ImportStaging_"
BACKUP_PREFIX = "B16_JP_VC_ImportBackup_"
MODEL_LABEL = "B16_JP_VC_Model"
FIT_MARGIN = 0.98
MODEL_YAW = 0.0


def all_actors():
    return list(actor_sub.get_all_level_actors())


def by_prefix(prefix):
    return [actor for actor in all_actors() if actor.get_actor_label().startswith(prefix)]


def bounds(actors):
    min_x = min_y = min_z = 10**18
    max_x = max_y = max_z = -10**18
    for actor in actors:
        origin, extent = actor.get_actor_bounds(False)
        min_x = min(min_x, origin.x - extent.x)
        max_x = max(max_x, origin.x + extent.x)
        min_y = min(min_y, origin.y - extent.y)
        max_y = max(max_y, origin.y + extent.y)
        min_z = min(min_z, origin.z - extent.z)
        max_z = max(max_z, origin.z + extent.z)
    return min_x, max_x, min_y, max_y, min_z, max_z


def snapshot(actors):
    result = []
    for actor in actors:
        location = actor.get_actor_location()
        rotation = actor.get_actor_rotation()
        scale = actor.get_actor_scale3d()
        result.append((
            actor.get_actor_label(),
            (location.x, location.y, location.z),
            (rotation.pitch, rotation.yaw, rotation.roll),
            (scale.x, scale.y, scale.z),
        ))
    return sorted(result)


def assert_snapshot(before, after, name):
    if len(before) != len(after):
        raise RuntimeError("%s actor count changed" % name)
    for old, new in zip(before, after):
        if old[0] != new[0]:
            raise RuntimeError("%s actor label changed" % name)
        for old_values, new_values in zip(old[1:], new[1:]):
            for old_value, new_value in zip(old_values, new_values):
                if abs(old_value - new_value) > 0.01:
                    raise RuntimeError("%s transform changed: %s" % (name, old[0]))


def imported_static_meshes():
    meshes = []
    for object_path in assetlib.list_assets(IMPORT_ROOT, recursive=True, include_folder=False):
        asset = assetlib.load_asset(object_path)
        if isinstance(asset, unreal.StaticMesh):
            meshes.append(asset)
    return meshes


def select_imported_meshes():
    meshes = imported_static_meshes()
    if len(meshes) == 1:
        return meshes
    named = [
        mesh for mesh in meshes
        if "visitor" in mesh.get_name().lower() or "jurassic" in mesh.get_name().lower()
    ]
    if len(named) == 1:
        return named
    raise RuntimeError(
        "Could not uniquely identify the imported Visitor Center StaticMesh: %s"
        % ", ".join(mesh.get_name() for mesh in meshes)
    )


gate_actors = by_prefix(B10_GATE_PREFIX)
if not gate_actors:
    raise RuntimeError("No B10_JP_GATE_ actors found; refusing to run.")
gate_snapshot = snapshot(gate_actors)
b10_snapshot = snapshot(by_prefix(B10_PREFIX))

b13_actors = by_prefix(B13_PREFIX)
if not b13_actors:
    raise RuntimeError("No B13_JP_VC_ actors found; refusing to run.")
b13_snapshot = snapshot(b13_actors)
b15_snapshot = snapshot(by_prefix(B15_PREFIX))
reference_b13 = [
    actor for actor in b13_actors
    if actor.get_actor_label() not in ("B13_JP_VC_Terrace", "B13_JP_VC_Forecourt")
]
if not reference_b13:
    raise RuntimeError("No usable B13 architectural reference actors found.")
target_min_x, target_max_x, target_min_y, target_max_y, target_min_z, target_max_z = bounds(reference_b13)
target_center_x = (target_min_x + target_max_x) * 0.5
target_center_y = (target_min_y + target_max_y) * 0.5

meshes = select_imported_meshes()
if len(meshes) != 1:
    raise RuntimeError(
        "Expected exactly one imported Visitor Center StaticMesh under %s; found %d"
        % (IMPORT_ROOT, len(meshes))
    )
model_mesh = meshes[0]

# Spawn a temporary measurement actor so imported GLB units and pivot placement
# are handled from the actual Unreal asset bounds rather than guessed values.
measurement = actor_sub.spawn_actor_from_class(
    unreal.StaticMeshActor,
    unreal.Vector(0.0, 0.0, 0.0),
    unreal.Rotator(0.0, MODEL_YAW, 0.0),
)
measurement.set_actor_label(STAGING_PREFIX + "Measurement")
measurement.static_mesh_component.set_static_mesh(model_mesh)
source_origin, source_extent = measurement.get_actor_bounds(False)
actor_sub.destroy_actor(measurement)

source_width_x = source_extent.x * 2.0
source_width_y = source_extent.y * 2.0
if source_width_x <= 0.0 or source_width_y <= 0.0:
    raise RuntimeError("Imported Visitor Center has invalid horizontal bounds.")

target_width_x = target_max_x - target_min_x
target_width_y = target_max_y - target_min_y
uniform_scale = min(target_width_x / source_width_x, target_width_y / source_width_y) * FIT_MARGIN

# Place the scaled imported bounds at the B13 reference center and ground its
# lowest point on the current B13 reference minimum Z.
world_x = target_center_x - source_origin.x * uniform_scale
world_y = target_center_y - source_origin.y * uniform_scale
world_z = target_min_z - source_origin.z * uniform_scale

# Clear interrupted import staging actors, then create the replacement. The
# previous B16 visual layer is removed only after the imported actor exists.
for actor in by_prefix(STAGING_PREFIX):
    actor_sub.destroy_actor(actor)

imported_actor = actor_sub.spawn_actor_from_class(
    unreal.StaticMeshActor,
    unreal.Vector(world_x, world_y, world_z),
    unreal.Rotator(0.0, MODEL_YAW, 0.0),
)
imported_actor.set_actor_label(STAGING_PREFIX + "Model")
imported_actor.static_mesh_component.set_static_mesh(model_mesh)
imported_actor.set_actor_scale3d(unreal.Vector(uniform_scale, uniform_scale, uniform_scale))

if not by_prefix(STAGING_PREFIX):
    raise RuntimeError("Imported Visitor Center staging actor was not created.")

previous_b16 = []
try:
    for index, actor in enumerate(all_actors()):
        label = actor.get_actor_label()
        if label.startswith(B16_PREFIX) and not label.startswith(STAGING_PREFIX):
            previous_b16.append((actor, label))
            actor.set_actor_label(BACKUP_PREFIX + "%03d" % index)

    for actor in all_actors():
        label = actor.get_actor_label()
        if label.startswith(B16_PREFIX) and not label.startswith(STAGING_PREFIX) and not label.startswith(BACKUP_PREFIX):
            actor_sub.destroy_actor(actor)

    imported_actor.set_actor_label(MODEL_LABEL)

    assert_snapshot(b13_snapshot, snapshot(by_prefix(B13_PREFIX)), "B13 Visitor Center")
    assert_snapshot(b15_snapshot, snapshot(by_prefix(B15_PREFIX)), "B15 site")
    assert_snapshot(b10_snapshot, snapshot(by_prefix(B10_PREFIX)), "B10 layer")
    assert_snapshot(gate_snapshot, snapshot(by_prefix(B10_GATE_PREFIX)), "B10 gate")

    if len(by_prefix(B16_PREFIX)) != 1:
        raise RuntimeError("Expected one imported B16 Visitor Center actor.")
    if by_prefix(STAGING_PREFIX):
        raise RuntimeError("Imported Visitor Center staging actors remain.")

    for actor in all_actors():
        if actor.get_actor_label().startswith(BACKUP_PREFIX):
            try:
                actor.set_is_temporarily_hidden_in_editor(True)
                actor_sub.destroy_actor(actor)
            except Exception:
                unreal.log_warning("Could not remove old B16 actor: %s" % actor.get_actor_label())
except Exception:
    actor_sub.destroy_actor(imported_actor)
    for actor, old_label in previous_b16:
        actor.set_actor_label(old_label)
    raise

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    unreal.EditorLevelLibrary.save_current_level()

unreal.log(
    "JP BUILD 1.6 IMPORT COMPLETE: imported=%s scale=%.6f; B13 reference preserved=%d; B15 untouched; gate protected=%d"
    % (model_mesh.get_name(), uniform_scale, len(b13_actors), len(gate_actors))
)
