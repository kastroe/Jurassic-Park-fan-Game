import unreal


# BUILD 1.5 - AUTHORITATIVE VISITOR CENTER CONSOLIDATION
#
# This pass assumes Build 1.4 has already produced the desired B13 scale.
# It never moves, scales, or rebuilds B13 architecture. It only removes old
# Visitor Center generations and replaces their support surfaces with three
# deterministic B15 helpers.

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assetlib = unreal.EditorAssetLibrary

B13_PREFIX = "B13_JP_VC_"
B10_GATE_PREFIX = "B10_JP_GATE_"
B15_PREFIX = "B15_JP_VC_"
STAGING_PREFIX = "B15_JP_VC_Staging_"

OBSOLETE_PREFIXES = (
    "B06_JP_VisitorCenter_",
    "B07_JP_VisitorCenter_",
    "B07_JP_VC_",
    "B08_JP_VC_",
    "B09_JP_VC_",
    "B10_JP_VC_",
    "B11_JP_VC_",
    "B12_JP_VC_",
    "B131_JP_VC_",
    "B14_JP_VC_",
)

LEGACY_B13_SURFACES = (
    "B13_JP_VC_Terrace",
    "B13_JP_VC_Forecourt",
)

STRUCTURAL_PREFIXES = (
    "B13_JP_VC_CentralBody",
    "B13_JP_VC_SideBody_",
    "B13_JP_VC_Connector_",
    "B13_JP_VC_EntranceBlock",
    "B13_JP_VC_Door",
    "B13_JP_VC_DoorPier_",
    "B13_JP_VC_DoorLintel",
)

cube = assetlib.load_asset("/Engine/BasicShapes/Cube.Cube")
if not cube:
    raise RuntimeError("Missing /Engine/BasicShapes/Cube.Cube")

MAT_DIR = "/Game/JPGenerated/Materials"


def load_mat(name):
    path = MAT_DIR + "/" + name
    return assetlib.load_asset(path) if assetlib.does_asset_exist(path) else None


M_STONE = load_mat("M_JP_Stone")
M_ASPHALT = load_mat("M_JP_Asphalt")


def all_actors():
    return list(actor_sub.get_all_level_actors())


def by_prefix(prefix):
    return [a for a in all_actors() if a.get_actor_label().startswith(prefix)]


def set_mat(actor, material):
    if material:
        actor.static_mesh_component.set_material(0, material)


def spawn_helper(label, location, scale, material):
    actor = actor_sub.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(location[0], location[1], location[2]),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    actor.set_actor_label(label)
    actor.static_mesh_component.set_static_mesh(cube)
    actor.set_actor_scale3d(unreal.Vector(scale[0], scale[1], scale[2]))
    set_mat(actor, material)
    return actor


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


def transform_snapshot(actors):
    snapshot = []
    for actor in actors:
        location = actor.get_actor_location()
        rotation = actor.get_actor_rotation()
        scale = actor.get_actor_scale3d()
        snapshot.append((
            actor.get_actor_label(),
            (location.x, location.y, location.z),
            (rotation.pitch, rotation.yaw, rotation.roll),
            (scale.x, scale.y, scale.z),
        ))
    return sorted(snapshot)


def assert_same_snapshot(before, after, name):
    if len(before) != len(after):
        raise RuntimeError("%s actor count changed" % name)
    for old, new in zip(before, after):
        if old[0] != new[0]:
            raise RuntimeError("%s actor label changed" % name)
        for old_values, new_values in zip(old[1:], new[1:]):
            for old_value, new_value in zip(old_values, new_values):
                if abs(old_value - new_value) > 0.01:
                    raise RuntimeError("%s transform changed: %s" % (name, old[0]))


# Capture the gate before cleanup. No cleanup operation below accepts its prefix.
gate_actors = by_prefix(B10_GATE_PREFIX)
if not gate_actors:
    raise RuntimeError("No B10_JP_GATE_ actors found; refusing to run without the protected gate.")
gate_snapshot = transform_snapshot(gate_actors)

# B13 is the immutable visual and scale baseline from Build 1.4.
b13_actors = by_prefix(B13_PREFIX)
if not b13_actors:
    raise RuntimeError("No B13_JP_VC_ actors found; run the existing baseline builds first.")
b13_snapshot = transform_snapshot(b13_actors)

# Compute the foundation from architectural masses only. Roofs, stairs,
# planters, and approach surfaces must not inflate the foundation footprint.
structural_actors = [
    actor for actor in by_prefix(B13_PREFIX)
    if any(actor.get_actor_label().startswith(prefix) for prefix in STRUCTURAL_PREFIXES)
]
if not structural_actors:
    raise RuntimeError("No structural B13 actors found for foundation bounds.")

struct_min_x, struct_max_x, struct_min_y, struct_max_y, struct_min_z, _ = bounds(structural_actors)
foundation_margin = 180.0
foundation_thickness = 80.0
foundation_min_x = struct_min_x - foundation_margin
foundation_max_x = struct_max_x + foundation_margin
foundation_min_y = struct_min_y - foundation_margin
foundation_max_y = struct_max_y + foundation_margin
foundation_top = struct_min_z - 8.0

# Build a compact arrival plaza from the entrance and stairs, rather than
# from the full three-pavilion footprint.
arrival_actors = [
    actor for actor in by_prefix(B13_PREFIX)
    if actor.get_actor_label().startswith("B13_JP_VC_EntranceBlock")
    or actor.get_actor_label().startswith("B13_JP_VC_Stair_")
]
if not arrival_actors:
    raise RuntimeError("No B13 entrance/stair actors found for plaza bounds.")

arrival_min_x, arrival_max_x, arrival_min_y, arrival_max_y, arrival_min_z, _ = bounds(arrival_actors)
plaza_margin_x = 300.0
plaza_margin_y = 350.0
plaza_thickness = 55.0
plaza_min_x = arrival_min_x - plaza_margin_x
plaza_max_x = arrival_max_x + plaza_margin_x
plaza_min_y = arrival_min_y - plaza_margin_y
plaza_max_y = arrival_max_y + plaza_margin_y
plaza_top = arrival_min_z - 6.0

# Clear only interrupted staging helpers from an earlier failed run.
for actor in by_prefix(STAGING_PREFIX):
    actor_sub.destroy_actor(actor)

spawn_helper(
    STAGING_PREFIX + "Foundation",
    (
        (foundation_min_x + foundation_max_x) * 0.5,
        (foundation_min_y + foundation_max_y) * 0.5,
        foundation_top - foundation_thickness * 0.5,
    ),
    (
        (foundation_max_x - foundation_min_x) / 100.0,
        (foundation_max_y - foundation_min_y) / 100.0,
        foundation_thickness / 100.0,
    ),
    M_STONE,
)

spawn_helper(
    STAGING_PREFIX + "Plaza",
    (
        (plaza_min_x + plaza_max_x) * 0.5,
        (plaza_min_y + plaza_max_y) * 0.5,
        plaza_top - plaza_thickness * 0.5,
    ),
    (
        (plaza_max_x - plaza_min_x) / 100.0,
        (plaza_max_y - plaza_min_y) / 100.0,
        plaza_thickness / 100.0,
    ),
    M_STONE,
)

# The arrival direction is -X, matching the existing Visitor Center layout.
road_length = 3600.0
road_width = (plaza_max_y - plaza_min_y) * 0.62
road_center_x = plaza_min_x - road_length * 0.5
road_top = plaza_top + 2.0
spawn_helper(
    STAGING_PREFIX + "Road",
    (road_center_x, (plaza_min_y + plaza_max_y) * 0.5, road_top - 12.5),
    (road_length / 100.0, road_width / 100.0, 25.0 / 100.0),
    M_ASPHALT,
)

staged_labels = sorted(actor.get_actor_label() for actor in by_prefix(STAGING_PREFIX))
expected_staged_labels = sorted(
    (
        STAGING_PREFIX + "Foundation",
        STAGING_PREFIX + "Plaza",
        STAGING_PREFIX + "Road",
    )
)
if staged_labels != expected_staged_labels:
    raise RuntimeError("Staging helpers are incomplete; refusing legacy cleanup.")

# Remove stale consolidator helpers and explicitly obsolete VC generations.
# Staged helpers use a separate namespace so cleanup cannot remove the new
# result before it has been created successfully.
for actor in all_actors():
    label = actor.get_actor_label()
    if label.startswith(B15_PREFIX) or any(label.startswith(prefix) for prefix in OBSOLETE_PREFIXES):
        if not label.startswith(STAGING_PREFIX):
            actor_sub.destroy_actor(actor)

# The old scaled terrace/forecourt are support surfaces, not architecture.
# Hide them so the new compact plaza and road are the only visible approach.
for actor in all_actors():
    if actor.get_actor_label() in LEGACY_B13_SURFACES:
        actor.set_is_temporarily_hidden_in_editor(True)

staged_names = {
    STAGING_PREFIX + "Foundation": "B15_JP_VC_Foundation",
    STAGING_PREFIX + "Plaza": "B15_JP_VC_Plaza",
    STAGING_PREFIX + "Road": "B15_JP_VC_Road",
}
for actor in all_actors():
    replacement = staged_names.get(actor.get_actor_label())
    if replacement:
        actor.set_actor_label(replacement)

# Verify that the protected baseline and gate were untouched before saving.
assert_same_snapshot(b13_snapshot, transform_snapshot(by_prefix(B13_PREFIX)), "B13 Visitor Center")
assert_same_snapshot(gate_snapshot, transform_snapshot(by_prefix(B10_GATE_PREFIX)), "B10 gate")

helper_count = len(by_prefix(B15_PREFIX))
if helper_count != 3:
    raise RuntimeError("Expected exactly 3 B15 helpers, found %d" % helper_count)

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    unreal.EditorLevelLibrary.save_current_level()

unreal.log(
    "JP BUILD 1.5 COMPLETE: consolidated Visitor Center; preserved B13=%d, protected gate=%d, helpers=%d"
    % (len(b13_actors), len(gate_actors), helper_count)
)
