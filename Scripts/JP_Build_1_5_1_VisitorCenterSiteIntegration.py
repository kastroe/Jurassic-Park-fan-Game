import unreal


# BUILD 1.5.1 - VISITOR CENTER SITE INTEGRATION
#
# This pass changes only B15 site helpers. B13 architecture and the B10 gate
# are read-only inputs and are never moved, scaled, hidden, relabeled, or
# destroyed.

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assetlib = unreal.EditorAssetLibrary

B13_PREFIX = "B13_JP_VC_"
B10_GATE_PREFIX = "B10_JP_GATE_"
B15_PREFIX = "B15_JP_VC_"
STAGING_PREFIX = "B15_JP_VC_SiteStaging_"
BACKUP_PREFIX = "B15_JP_VC_SiteBackup_"

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
if not M_STONE or not M_ASPHALT:
    raise RuntimeError("Required Visitor Center site materials are missing.")


def all_actors():
    return list(actor_sub.get_all_level_actors())


def by_prefix(prefix):
    return [a for a in all_actors() if a.get_actor_label().startswith(prefix)]


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


def spawn_site(label, location, dimensions, material, yaw=0.0):
    actor = actor_sub.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(location[0], location[1], location[2]),
        unreal.Rotator(0.0, yaw, 0.0),
    )
    actor.set_actor_label(label)
    actor.static_mesh_component.set_static_mesh(cube)
    actor.static_mesh_component.set_material(0, material)
    actor.set_actor_scale3d(unreal.Vector(
        dimensions[0] / 100.0,
        dimensions[1] / 100.0,
        dimensions[2] / 100.0,
    ))
    return actor


def slab(label, min_x, max_x, min_y, max_y, top_z, thickness, material, yaw=0.0):
    return spawn_site(
        label,
        ((min_x + max_x) * 0.5, (min_y + max_y) * 0.5, top_z - thickness * 0.5),
        (max_x - min_x, max_y - min_y, thickness),
        material,
        yaw,
    )


gate_actors = by_prefix(B10_GATE_PREFIX)
if not gate_actors:
    raise RuntimeError("No B10_JP_GATE_ actors found; refusing to run.")
gate_snapshot = snapshot(gate_actors)

b13_actors = by_prefix(B13_PREFIX)
if not b13_actors:
    raise RuntimeError("No B13_JP_VC_ actors found; refusing to run.")
b13_snapshot = snapshot(b13_actors)

structural_actors = [
    actor for actor in b13_actors
    if any(actor.get_actor_label().startswith(prefix) for prefix in STRUCTURAL_PREFIXES)
]
if not structural_actors:
    raise RuntimeError("No structural B13 actors found; refusing to run.")

stairs = [
    actor for actor in b13_actors
    if actor.get_actor_label().startswith("B13_JP_VC_Stair_")
]
if not stairs:
    raise RuntimeError("No B13 stair actors found; refusing to run.")

struct_min_x, struct_max_x, struct_min_y, struct_max_y, struct_min_z, _ = bounds(structural_actors)
front_stair = min(stairs, key=lambda actor: bounds([actor])[0])
front_stair_min_x, front_stair_max_x, front_stair_min_y, front_stair_max_y, _, front_stair_max_z = bounds([front_stair])

# Keep the foundation tight and thin so it reads as a building footing, not a
# second platform. The low front step softens its hard edge into the site.
foundation_margin = 100.0
foundation_thickness = 45.0
foundation_min_x = struct_min_x - foundation_margin
foundation_max_x = struct_max_x + foundation_margin
foundation_min_y = struct_min_y - foundation_margin
foundation_max_y = struct_max_y + foundation_margin
foundation_top = struct_min_z - 5.0

# The plaza follows only the lower stair arrival zone. It is intentionally
# split into a landing, angled side wings, and a small front apron.
stair_run = front_stair_max_x - front_stair_min_x
stair_width = front_stair_max_y - front_stair_min_y
landing_length = max(900.0, min(1800.0, stair_run * 0.35))
landing_width = max(1400.0, min(2600.0, stair_width * 0.72))
landing_min_x = front_stair_min_x - 180.0
landing_max_x = landing_min_x + landing_length
landing_center_y = (front_stair_min_y + front_stair_max_y) * 0.5
landing_min_y = landing_center_y - landing_width * 0.5
landing_max_y = landing_center_y + landing_width * 0.5
plaza_top = front_stair_max_z - 2.0

wing_length = min(1150.0, landing_length * 0.72)
wing_width = min(850.0, max(550.0, landing_width * 0.34))
wing_center_x = landing_min_x + landing_length * 0.56
wing_overlap = 120.0
front_apron_length = 650.0
front_apron_min_x = landing_min_x - front_apron_length
front_apron_max_x = landing_min_x + 40.0
front_apron_width = landing_width * 0.78

# The road is short, tapered by two segments, and narrower than the plaza.
road_near_length = 650.0
road_far_length = 1050.0
road_near_min_x = front_apron_min_x - road_near_length - 60.0
road_near_max_x = front_apron_min_x + 40.0
road_far_min_x = road_near_min_x - road_far_length
road_far_max_x = road_near_min_x + 40.0
road_near_width = front_apron_width * 0.72
road_far_width = front_apron_width * 0.52
road_center_y = landing_center_y

# Clear interrupted staging actors only. Existing B15 helpers remain until
# every new site piece has been staged successfully.
for actor in by_prefix(STAGING_PREFIX):
    actor_sub.destroy_actor(actor)

staged = []
staged.append(slab(
    STAGING_PREFIX + "Foundation",
    foundation_min_x, foundation_max_x,
    foundation_min_y, foundation_max_y,
    foundation_top, foundation_thickness, M_STONE,
))

# A shallow lower step is narrower than the foundation and sits below its top.
staged.append(slab(
    STAGING_PREFIX + "FoundationTransition",
    foundation_min_x - 80.0, foundation_min_x + 420.0,
    foundation_min_y + foundation_margin * 1.5,
    foundation_max_y - foundation_margin * 1.5,
    foundation_top - 5.0, 28.0, M_STONE,
))

staged.append(slab(
    STAGING_PREFIX + "Plaza",
    landing_min_x, landing_max_x,
    landing_min_y, landing_max_y,
    plaza_top, 38.0, M_STONE,
))
staged.append(slab(
    STAGING_PREFIX + "Plaza_Apron",
    front_apron_min_x, front_apron_max_x,
    landing_center_y - front_apron_width * 0.5,
    landing_center_y + front_apron_width * 0.5,
    plaza_top - 7.0, 32.0, M_STONE,
))

wing_y_offset = landing_width * 0.5 + wing_width * 0.5 - wing_overlap
staged.append(slab(
    STAGING_PREFIX + "Plaza_Left",
    wing_center_x - wing_length * 0.5, wing_center_x + wing_length * 0.5,
    landing_center_y + wing_y_offset - wing_width * 0.5,
    landing_center_y + wing_y_offset + wing_width * 0.5,
    plaza_top - 12.0, 30.0, M_STONE, 10.0,
))
staged.append(slab(
    STAGING_PREFIX + "Plaza_Right",
    wing_center_x - wing_length * 0.5, wing_center_x + wing_length * 0.5,
    landing_center_y - wing_y_offset - wing_width * 0.5,
    landing_center_y - wing_y_offset + wing_width * 0.5,
    plaza_top - 12.0, 30.0, M_STONE, -10.0,
))

staged.append(slab(
    STAGING_PREFIX + "Road",
    road_near_min_x, road_near_max_x,
    road_center_y - road_near_width * 0.5,
    road_center_y + road_near_width * 0.5,
    plaza_top - 14.0, 24.0, M_ASPHALT,
))
staged.append(slab(
    STAGING_PREFIX + "Road_Far",
    road_far_min_x, road_far_max_x,
    road_center_y - road_far_width * 0.5,
    road_center_y + road_far_width * 0.5,
    plaza_top - 18.0, 22.0, M_ASPHALT,
))

expected_staging = sorted(actor.get_actor_label() for actor in staged)
if expected_staging != sorted(actor.get_actor_label() for actor in by_prefix(STAGING_PREFIX)):
    raise RuntimeError("Site staging is incomplete; refusing to replace current B15 helpers.")

staged_names = {
    STAGING_PREFIX + "Foundation": "B15_JP_VC_Foundation",
    STAGING_PREFIX + "FoundationTransition": "B15_JP_VC_FoundationTransition",
    STAGING_PREFIX + "Plaza": "B15_JP_VC_Plaza",
    STAGING_PREFIX + "Plaza_Apron": "B15_JP_VC_Plaza_Apron",
    STAGING_PREFIX + "Plaza_Left": "B15_JP_VC_Plaza_Left",
    STAGING_PREFIX + "Plaza_Right": "B15_JP_VC_Plaza_Right",
    STAGING_PREFIX + "Road": "B15_JP_VC_Road",
    STAGING_PREFIX + "Road_Far": "B15_JP_VC_Road_Far",
}

# Keep the previous B15 result recoverable while the staged result is swapped
# in. No B13 or B10 actor is part of this replacement transaction.
previous_helpers = []
try:
    for index, actor in enumerate(all_actors()):
        label = actor.get_actor_label()
        if label.startswith(B15_PREFIX) and not label.startswith(STAGING_PREFIX):
            previous_helpers.append((actor, label))
            actor.set_actor_label(BACKUP_PREFIX + "%03d" % index)

    for actor in all_actors():
        label = actor.get_actor_label()
        if label.startswith(B15_PREFIX) and not label.startswith(STAGING_PREFIX) and not label.startswith(BACKUP_PREFIX):
            actor_sub.destroy_actor(actor)

    for actor in all_actors():
        replacement = staged_names.get(actor.get_actor_label())
        if replacement:
            actor.set_actor_label(replacement)

    assert_snapshot(b13_snapshot, snapshot(by_prefix(B13_PREFIX)), "B13 Visitor Center")
    assert_snapshot(gate_snapshot, snapshot(by_prefix(B10_GATE_PREFIX)), "B10 gate")

    final_labels = sorted(
        actor.get_actor_label() for actor in by_prefix(B15_PREFIX)
        if not actor.get_actor_label().startswith(BACKUP_PREFIX)
    )
    if final_labels != sorted(staged_names.values()):
        raise RuntimeError("Final B15 site helper set is incomplete.")

    for actor in all_actors():
        if actor.get_actor_label().startswith(BACKUP_PREFIX):
            actor_sub.destroy_actor(actor)

    if by_prefix(BACKUP_PREFIX) or by_prefix(STAGING_PREFIX):
        raise RuntimeError("B15 site cleanup left backup or staging actors behind.")
except Exception:
    # Restore the prior site layer if the swap or its validation fails.
    for actor in staged:
        actor_sub.destroy_actor(actor)
    for actor, old_label in previous_helpers:
        actor.set_actor_label(old_label)
    raise

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    unreal.EditorLevelLibrary.save_current_level()

unreal.log(
    "JP BUILD 1.5.1 COMPLETE: integrated Visitor Center site; B13=%d, gate=%d, B15 helpers=%d"
    % (len(b13_actors), len(gate_actors), len(staged_names))
)
