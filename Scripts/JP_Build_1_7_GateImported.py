import unreal


# BUILD 1.7 - IMPORTED JURASSIC PARK GATE PLACEMENT
#
# Run after importing the GLB into /Game/JPImported/Gate. The imported model
# becomes a new B17 gate while B10 remains visible and untouched as fallback.

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assetlib = unreal.EditorAssetLibrary

IMPORT_ROOT = "/Game/JPImported/Gate"
B10_GATE_PREFIX = "B10_JP_GATE_"
B17_PREFIX = "B17_JP_GATE_"
STAGING_PREFIX = "B17_JP_GATE_ImportStaging_"
BACKUP_PREFIX = "B17_JP_GATE_ImportBackup_"
MODEL_LABEL = "B17_JP_GATE_Model"
MODEL_YAW = 90.0
FIT_MARGIN = 0.98


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


def editor_hidden_state(actor):
    for method_name in ("get_is_temporarily_hidden_in_editor", "is_hidden_ed"):
        method = getattr(actor, method_name, None)
        if callable(method):
            return bool(method())
    try:
        return bool(actor.get_editor_property("bIsTemporarilyHiddenInEditor"))
    except Exception:
        raise RuntimeError("Cannot inspect editor-hidden state for %s" % actor.get_actor_label())


def imported_static_meshes():
    meshes = []
    for object_path in assetlib.list_assets(IMPORT_ROOT, recursive=True, include_folder=False):
        asset = assetlib.load_asset(object_path)
        if isinstance(asset, unreal.StaticMesh):
            meshes.append(asset)
    return meshes


def select_imported_mesh():
    meshes = imported_static_meshes()
    if len(meshes) == 1:
        return meshes[0]
    raise RuntimeError(
        "Expected exactly one imported gate StaticMesh; found: %s"
        % ", ".join(mesh.get_name() for mesh in meshes)
    )


b10_actors = by_prefix(B10_GATE_PREFIX)
if not b10_actors:
    raise RuntimeError("No B10_JP_GATE_ actors found; refusing to run.")
b10_snapshot = snapshot(b10_actors)

reference_gate = [
    actor for actor in b10_actors
    if "Road" not in actor.get_actor_label()
    and "Flame" not in actor.get_actor_label()
    and "Torch" not in actor.get_actor_label()
]
if not reference_gate:
    raise RuntimeError("No structural B10 gate actors found.")
target_min_x, target_max_x, target_min_y, target_max_y, target_min_z, target_max_z = bounds(reference_gate)
target_center_x = (target_min_x + target_max_x) * 0.5
target_center_y = (target_min_y + target_max_y) * 0.5
target_width_y = target_max_y - target_min_y
target_height_z = target_max_z - target_min_z

model_mesh = select_imported_mesh()

measurement = actor_sub.spawn_actor_from_class(
    unreal.StaticMeshActor,
    unreal.Vector(0.0, 0.0, 0.0),
    unreal.Rotator(0.0, MODEL_YAW, 0.0),
)
try:
    measurement.set_actor_label(STAGING_PREFIX + "Measurement")
    measurement.static_mesh_component.set_static_mesh(model_mesh)
    source_origin, source_extent = measurement.get_actor_bounds(False)
finally:
    actor_sub.destroy_actor(measurement)

source_width_y = source_extent.y * 2.0
source_height_z = source_extent.z * 2.0
if source_width_y <= 0.0 or source_height_z <= 0.0:
    raise RuntimeError("Imported gate has invalid width/height bounds after orientation.")

uniform_scale = min(target_width_y / source_width_y, target_height_z / source_height_z) * FIT_MARGIN
world_x = target_center_x - source_origin.x * uniform_scale
world_y = target_center_y - source_origin.y * uniform_scale
world_z = target_min_z - (source_origin.z - source_extent.z) * uniform_scale

for actor in by_prefix(STAGING_PREFIX):
    actor_sub.destroy_actor(actor)

imported_actor = None
try:
    imported_actor = actor_sub.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(world_x, world_y, world_z),
        unreal.Rotator(0.0, MODEL_YAW, 0.0),
    )
    imported_actor.set_actor_label(STAGING_PREFIX + "Model")
    imported_actor.static_mesh_component.set_static_mesh(model_mesh)
    imported_actor.set_actor_scale3d(unreal.Vector(uniform_scale, uniform_scale, uniform_scale))

    if len(by_prefix(STAGING_PREFIX)) != 1:
        raise RuntimeError("Imported gate staging actor was not created uniquely.")
except Exception:
    for actor in all_actors():
        if actor.get_actor_label().startswith(STAGING_PREFIX):
            actor_sub.destroy_actor(actor)
    raise

previous_b17 = []


def restore_previous(imported_actor, previous):
    errors = []
    try:
        actor_sub.destroy_actor(imported_actor)
    except Exception as error:
        errors.append(error)
    for actor, old_label, old_hidden in previous:
        try:
            actor.set_actor_label(old_label)
            actor.set_is_temporarily_hidden_in_editor(old_hidden)
        except Exception as error:
            errors.append(error)
    if errors:
        raise RuntimeError("B17 rollback encountered %d restoration error(s)." % len(errors))


try:
    for index, actor in enumerate(all_actors()):
        label = actor.get_actor_label()
        if label.startswith(B17_PREFIX) and not label.startswith(STAGING_PREFIX):
            previous_b17.append((actor, label, editor_hidden_state(actor)))
            actor.set_actor_label(BACKUP_PREFIX + "%03d" % index)

    for actor in all_actors():
        label = actor.get_actor_label()
        if label.startswith(B17_PREFIX) and not label.startswith(STAGING_PREFIX) and not label.startswith(BACKUP_PREFIX):
            actor_sub.destroy_actor(actor)

    imported_actor.set_actor_label(MODEL_LABEL)
    assert_snapshot(b10_snapshot, snapshot(by_prefix(B10_GATE_PREFIX)), "B10 gate")

    if len([actor for actor in by_prefix(B17_PREFIX) if actor.get_actor_label() == MODEL_LABEL]) != 1:
        raise RuntimeError("Expected one imported B17 gate actor.")

    for actor in all_actors():
        if actor.get_actor_label().startswith(BACKUP_PREFIX):
            actor.set_is_temporarily_hidden_in_editor(True)
except Exception:
    restore_previous(imported_actor, previous_b17)
    raise

def save_level():
    try:
        if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level() is True:
            return True
    except Exception:
        pass
    try:
        return unreal.EditorLevelLibrary.save_current_level() is True
    except Exception:
        return False


if not save_level():
    restore_previous(imported_actor, previous_b17)
    if not save_level():
        raise RuntimeError("Gate replacement and rollback could not be persisted.")
    raise RuntimeError("Gate replacement was rolled back because the level could not be saved.")

# The new gate is now safely saved. Retire hidden prior B17 imports; a failed
# cleanup leaves them hidden rather than exposing duplicate gates.
for actor in all_actors():
    if actor.get_actor_label().startswith(BACKUP_PREFIX):
        try:
            actor_sub.destroy_actor(actor)
        except Exception:
            unreal.log_warning("Could not remove old B17 gate actor: %s" % actor.get_actor_label())
if not save_level():
    unreal.log_warning("New B17 gate is saved; old hidden B17 cleanup could not be persisted.")

unreal.log(
    "JP BUILD 1.7 GATE IMPORT COMPLETE: imported=%s scale=%.6f; B10 fallback preserved=%d"
    % (model_mesh.get_name(), uniform_scale, len(b10_actors))
)
