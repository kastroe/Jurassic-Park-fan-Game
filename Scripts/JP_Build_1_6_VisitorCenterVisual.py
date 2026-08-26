import unreal


# BUILD 1.6 - CLEAN VISITOR CENTER VISUAL GENERATION
#
# B13 is a spatial reference only. This build creates a new architectural
# blockout under B16_JP_VC_ and intentionally leaves B13 and B15 visible for
# visual comparison. B10_JP_GATE_ is read-only and protected.

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assetlib = unreal.EditorAssetLibrary

B13_PREFIX = "B13_JP_VC_"
B10_GATE_PREFIX = "B10_JP_GATE_"
B16_PREFIX = "B16_JP_VC_"
STAGING_PREFIX = "B16_JP_VC_Staging_"
BACKUP_PREFIX = "B16_JP_VC_Backup_"

VCX = -10080.0
VCY = -3024.0
FALLBACK_BASE_Z = 3205.9

cube = assetlib.load_asset("/Engine/BasicShapes/Cube.Cube")
cylinder = assetlib.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
cone = assetlib.load_asset("/Engine/BasicShapes/Cone.Cone")
sphere = assetlib.load_asset("/Engine/BasicShapes/Sphere.Sphere")
if not cube or not cylinder or not cone or not sphere:
    raise RuntimeError("Required engine primitive meshes are missing.")

MAT_DIR = "/Game/JPGenerated/Materials"


def load_mat(name):
    path = MAT_DIR + "/" + name
    return assetlib.load_asset(path) if assetlib.does_asset_exist(path) else None


M_STONE = load_mat("M_JP_Stone")
M_CONCRETE = load_mat("M_JP_Concrete")
M_ROOF = load_mat("M_JP_ThatchApprox")
M_ROOF_RED = load_mat("M_JP_RoofRed") or M_ROOF
M_GLASS = load_mat("M_JP_GlassDark")
M_WOOD = load_mat("M_JP_DarkWood")
M_ASPHALT = load_mat("M_JP_Asphalt")
if not all((M_STONE, M_CONCRETE, M_ROOF, M_GLASS, M_WOOD, M_ASPHALT)):
    raise RuntimeError("Required Visitor Center materials are missing.")


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


def reference_base_z(b13_actors):
    terraces = [actor for actor in b13_actors if actor.get_actor_label() == "B13_JP_VC_Terrace"]
    if terraces:
        _, _, _, _, _, top_z = bounds(terraces)
        if -100000.0 < top_z < 100000.0:
            return top_z
    return FALLBACK_BASE_Z


gate_actors = by_prefix(B10_GATE_PREFIX)
if not gate_actors:
    raise RuntimeError("No B10_JP_GATE_ actors found; refusing to run.")
gate_snapshot = snapshot(gate_actors)

b13_actors = by_prefix(B13_PREFIX)
if not b13_actors:
    raise RuntimeError("No B13_JP_VC_ actors found; refusing to run.")
b13_snapshot = snapshot(b13_actors)
BASE_Z = reference_base_z(b13_actors)


def spawn_mesh(label, mesh, x, y, z, scale, material, yaw=0.0, pitch=0.0, roll=0.0):
    actor = actor_sub.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(VCX + x, VCY + y, z),
        unreal.Rotator(pitch, yaw, roll),
    )
    created_staging.append(actor)
    actor.set_actor_label(label)
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_material(0, material)
    actor.set_actor_scale3d(unreal.Vector(scale[0], scale[1], scale[2]))
    return actor


def stage_name(name):
    return STAGING_PREFIX + name


def cube_dim(name, x, y, z, dx, dy, dz, material, yaw=0.0):
    return spawn_mesh(stage_name(name), cube, x, y, BASE_Z + z, (dx / 100.0, dy / 100.0, dz / 100.0), material, yaw)


def cyl_dim(name, x, y, z, diameter, height, material, yaw=0.0):
    return spawn_mesh(stage_name(name), cylinder, x, y, BASE_Z + z, (diameter / 100.0, diameter / 100.0, height / 100.0), material, yaw)


def cone_dim(name, x, y, z, diameter, height, material, yaw=0.0):
    return spawn_mesh(stage_name(name), cone, x, y, BASE_Z + z, (diameter / 100.0, diameter / 100.0, height / 100.0), material, yaw)


def sphere_dim(name, x, y, z, diameter, height, material):
    return spawn_mesh(stage_name(name), sphere, x, y, BASE_Z + z, (diameter / 100.0, diameter / 100.0, height / 100.0), material)


# Clear only an interrupted prior B16 staging set. Existing completed B16 is
# retained until the replacement set has fully spawned and validated.
for actor in by_prefix(STAGING_PREFIX):
    actor_sub.destroy_actor(actor)

created_staging = []
staged = []

# ---------------------------------------------------------------------------
# CENTRAL ROTUNDA: the dominant mass, wide and low rather than a tall spike.
# ---------------------------------------------------------------------------
staged.append(cyl_dim("CentralPlinth", 650, 0, 150, 6900, 300, M_STONE))
staged.append(cyl_dim("CentralBody", 650, 0, 1120, 6100, 1900, M_CONCRETE))
staged.append(cyl_dim("CentralGlassBand", 650, 0, 1850, 6250, 360, M_GLASS))
staged.append(cyl_dim("CentralEave", 650, 0, 2080, 7600, 180, M_STONE))
staged.append(cone_dim("CentralRoof", 650, 0, 2440, 8200, 900, M_ROOF_RED))
staged.append(cyl_dim("CentralCupolaBody", 650, 0, 3220, 1650, 800, M_CONCRETE))
staged.append(cyl_dim("CentralCupolaBand", 650, 0, 3520, 1750, 180, M_GLASS))
staged.append(cone_dim("CentralCupolaRoof", 650, 0, 3820, 2200, 520, M_ROOF_RED))

# ---------------------------------------------------------------------------
# SIDE PAVILIONS: clearly smaller, but aligned to the same datum and roof
# language. Their connector masses overlap both rotunda footprints.
# ---------------------------------------------------------------------------
for side, sy in (("L", -9000.0), ("R", 9000.0)):
    staged.append(cyl_dim("SidePlinth_" + side, 900, sy, 130, 4550, 260, M_STONE))
    staged.append(cyl_dim("SideBody_" + side, 900, sy, 880, 4050, 1450, M_CONCRETE))
    staged.append(cyl_dim("SideGlassBand_" + side, 900, sy, 1430, 4160, 280, M_GLASS))
    staged.append(cyl_dim("SideEave_" + side, 900, sy, 1650, 5000, 150, M_STONE))
    staged.append(cone_dim("SideRoof_" + side, 900, sy, 1960, 5350, 660, M_ROOF_RED))
    staged.append(cyl_dim("SideCupolaBody_" + side, 900, sy, 2580, 900, 470, M_CONCRETE))
    staged.append(cone_dim("SideCupolaRoof_" + side, 900, sy, 2880, 1250, 360, M_ROOF_RED))

# Low enclosed connectors make the three circles read as one building.
for side, sy, yaw in (("L", -4550.0, -4.0), ("R", 4550.0, 4.0)):
    staged.append(cube_dim("ConnectorBody_" + side, 760, sy, 720, 2850, 7000, 1050, M_STONE, yaw))
    staged.append(cube_dim("ConnectorGlass_" + side, 600, sy, 1320, 1800, 6800, 360, M_GLASS, yaw))
    staged.append(cube_dim("ConnectorRoof_" + side, 760, sy, 1750, 3300, 7200, 260, M_ROOF_RED, yaw))

# ---------------------------------------------------------------------------
# PROJECTING CENTRAL ENTRANCE AND FRONT FACADE.
# ---------------------------------------------------------------------------
staged.append(cube_dim("EntranceMass", -2850, 0, 1040, 1900, 3000, 2000, M_STONE))
staged.append(cube_dim("EntranceCanopy", -3650, 0, 2140, 1500, 3400, 360, M_ROOF_RED))
staged.append(cube_dim("Door", -3970, 0, 1000, 220, 1550, 1800, M_WOOD))
for side, sy in (("L", -980.0), ("R", 980.0)):
    staged.append(cube_dim("DoorPier_" + side, -4000, sy, 1040, 300, 300, 2100, M_STONE))
staged.append(cube_dim("DoorLintel", -4000, 0, 2110, 320, 2500, 320, M_STONE))

# Seven broad front window bays with substantial stone columns between them.
front_x = -2380.0
window_y = (-2700.0, -1800.0, -900.0, 0.0, 900.0, 1800.0, 2700.0)
for index, sy in enumerate(window_y):
    staged.append(cube_dim("Window_%02d" % index, front_x, sy, 1020, 180, 620, 980, M_GLASS))
for index, sy in enumerate((-3150.0, -2250.0, -1350.0, -450.0, 450.0, 1350.0, 2250.0, 3150.0)):
    staged.append(cyl_dim("FrontColumn_%02d" % index, front_x - 40.0, sy, 1080, 240, 1500, M_STONE))

# Side connector arcades: repeated vertical bays, intentionally aligned with
# the central columns rather than random detached cubes.
for side, sy in (("L", -4550.0), ("R", 4550.0)):
    for index, dx in enumerate((-420.0, 420.0)):
        staged.append(cyl_dim("ArcadeColumn_%s_%d" % (side, index), dx, sy, 850, 240, 1450, M_STONE))

# ---------------------------------------------------------------------------
# ARRIVAL ELEMENTS: broad centered stair and angled retaining/planter walls.
# These are part of the visual building generation, not the B15 site layer.
# ---------------------------------------------------------------------------
for index in range(10):
    x = -6500.0 + index * 270.0
    width = 2500.0 + index * 130.0
    z = 90.0 + index * 115.0
    staged.append(cube_dim("Stair_%02d" % index, x, 0, z, 300.0, width, 180.0, M_STONE))

staged.append(cube_dim("PlanterWall_L", -5200, -2050, 390, 2100, 360, 780, M_STONE, -12.0))
staged.append(cube_dim("PlanterWall_R", -5200, 2050, 390, 2100, 360, 780, M_STONE, 12.0))
staged.append(cube_dim("PlanterCap_L", -5200, -2050, 810, 2200, 440, 140, M_CONCRETE, -12.0))
staged.append(cube_dim("PlanterCap_R", -5200, 2050, 810, 2200, 440, 140, M_CONCRETE, 12.0))

# A restrained central arrival strip gives the new structure a readable base
# while leaving the existing B15 site integration available for comparison.
staged.append(cube_dim("ArrivalPlinth", -3600, 0, 55, 3500, 5000, 110, M_CONCRETE))

expected_staging = sorted(actor.get_actor_label() for actor in staged)
if expected_staging != sorted(actor.get_actor_label() for actor in by_prefix(STAGING_PREFIX)):
    raise RuntimeError("B16 staging set is incomplete; refusing replacement.")

previous_b16 = []
try:
    # Preserve the previous generated set until the new set has been renamed
    # and protected-actor validation has passed.
    for index, actor in enumerate(all_actors()):
        label = actor.get_actor_label()
        if label.startswith(B16_PREFIX) and not label.startswith(STAGING_PREFIX):
            previous_b16.append((actor, label))
            actor.set_actor_label(BACKUP_PREFIX + "%03d" % index)

    for actor in all_actors():
        label = actor.get_actor_label()
        if label.startswith(B16_PREFIX) and not label.startswith(STAGING_PREFIX) and not label.startswith(BACKUP_PREFIX):
            actor_sub.destroy_actor(actor)

    for actor in all_actors():
        label = actor.get_actor_label()
        if label.startswith(STAGING_PREFIX):
            actor.set_actor_label(B16_PREFIX + label[len(STAGING_PREFIX):])

    assert_snapshot(b13_snapshot, snapshot(by_prefix(B13_PREFIX)), "B13 Visitor Center")
    assert_snapshot(gate_snapshot, snapshot(by_prefix(B10_GATE_PREFIX)), "B10 gate")

    final_b16 = [
        actor for actor in by_prefix(B16_PREFIX)
        if not actor.get_actor_label().startswith(BACKUP_PREFIX)
    ]
    if len(final_b16) != len(staged):
        raise RuntimeError("Expected %d B16 actors, found %d" % (len(staged), len(final_b16)))
    if by_prefix(STAGING_PREFIX):
        raise RuntimeError("B16 staging actors remain after replacement.")

    for actor in all_actors():
        if actor.get_actor_label().startswith(BACKUP_PREFIX):
            try:
                actor.set_is_temporarily_hidden_in_editor(True)
                actor_sub.destroy_actor(actor)
            except Exception:
                unreal.log_warning("Could not remove old B16 actor: %s" % actor.get_actor_label())
except Exception:
    for actor in created_staging:
        actor_sub.destroy_actor(actor)
    for actor, old_label in previous_b16:
        actor.set_actor_label(old_label)
    raise

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    unreal.EditorLevelLibrary.save_current_level()

unreal.log(
    "JP BUILD 1.6 COMPLETE: clean Visitor Center visual generated; B16=%d, B13 reference preserved, gate protected=%d"
    % (len(final_b16), len(gate_actors))
)
