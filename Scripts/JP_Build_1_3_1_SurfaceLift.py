import unreal

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assetlib = unreal.EditorAssetLibrary

CUBE = assetlib.load_asset('/Engine/BasicShapes/Cube.Cube')

# ----------------------------
# Build 1.3.1 — Surface Lift
# Fixes B13 visitor center appearing buried / too low.
# This lifts the whole B13 group together and creates
# one clean podium under it so it reads like one object.
# ----------------------------

LIFT_Z = 260.0
PODIUM_MARGIN_X = 350.0
PODIUM_MARGIN_Y = 350.0
PODIUM_THICKNESS = 40.0
PODIUM_GAP = 5.0

MAT_DIR = '/Game/JPGenerated/Materials'
def load_mat(name):
    path = MAT_DIR + '/' + name
    return assetlib.load_asset(path) if assetlib.does_asset_exist(path) else None
M_STONE = load_mat('M_JP_Stone')
M_CONCRETE = load_mat('M_JP_Concrete')
PODIUM_MAT = M_STONE if M_STONE else M_CONCRETE

def by_prefix(prefix):
    return [a for a in actor_sub.get_all_level_actors() if a.get_actor_label().startswith(prefix)]

def destroy_if_exists(label):
    for a in actor_sub.get_all_level_actors():
        if a.get_actor_label() == label:
            actor_sub.destroy_actor(a)

vc_actors = by_prefix('B13_JP_VC_')
if not vc_actors:
    unreal.log_error('BUILD 1.3.1: No B13_JP_VC_ actors found. Run Build 1.3 first.')
    raise RuntimeError('No B13_JP_VC_ actors found')

# Remove any older 1.3.1 podium / helpers.
destroy_if_exists('B131_JP_VC_Podium')
destroy_if_exists('B131_JP_VC_PodiumCap')

# Hide older terraces if they exist so only the lifted result reads clearly.
for label in ('B13_JP_VC_Terrace','B12_JP_VC_Terrace','B11_JP_VC_Terrace','B10_JP_VC_Terrace'):
    for a in actor_sub.get_all_level_actors():
        if a.get_actor_label() == label:
            try:
                a.set_is_temporarily_hidden_in_editor(True)
            except Exception:
                pass

# Move every B13 actor up together.
for a in vc_actors:
    loc = a.get_actor_location()
    a.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + LIFT_Z), False, False)

# Compute bounds after the lift.
min_x = min_y = min_z = 10**18
max_x = max_y = max_z = -10**18
for a in vc_actors:
    origin, extent = a.get_actor_bounds(False)
    min_x = min(min_x, origin.x - extent.x)
    max_x = max(max_x, origin.x + extent.x)
    min_y = min(min_y, origin.y - extent.y)
    max_y = max(max_y, origin.y + extent.y)
    min_z = min(min_z, origin.z - extent.z)
    max_z = max(max_z, origin.z + extent.z)

# Build one podium under the whole visitor center.
width_x = (max_x - min_x) + PODIUM_MARGIN_X * 2.0
width_y = (max_y - min_y) + PODIUM_MARGIN_Y * 2.0
center_x = (min_x + max_x) * 0.5
center_y = (min_y + max_y) * 0.5
# Set top of podium slightly under the lowest VC component.
podium_center_z = (min_z - PODIUM_GAP) - (PODIUM_THICKNESS * 0.5)

podium = actor_sub.spawn_actor_from_class(
    unreal.StaticMeshActor,
    unreal.Vector(center_x, center_y, podium_center_z),
    unreal.Rotator(0.0, 0.0, 0.0)
)
podium.set_actor_label('B131_JP_VC_Podium')
podium.static_mesh_component.set_static_mesh(CUBE)
podium.static_mesh_component.set_material(0, PODIUM_MAT)
podium.set_actor_scale3d(unreal.Vector(width_x / 100.0, width_y / 100.0, PODIUM_THICKNESS / 100.0))

# Thin cap on top so the surface reads cleanly.
cap_thickness = 8.0
cap_center_z = (min_z - 1.5) - (cap_thickness * 0.5)
podium_cap = actor_sub.spawn_actor_from_class(
    unreal.StaticMeshActor,
    unreal.Vector(center_x, center_y, cap_center_z),
    unreal.Rotator(0.0, 0.0, 0.0)
)
podium_cap.set_actor_label('B131_JP_VC_PodiumCap')
podium_cap.static_mesh_component.set_static_mesh(CUBE)
podium_cap.static_mesh_component.set_material(0, PODIUM_MAT)
podium_cap.set_actor_scale3d(unreal.Vector((width_x+60.0) / 100.0, (width_y+60.0) / 100.0, cap_thickness / 100.0))

# Focus the editor camera on the lifted group if possible.
try:
    level_sub.editor_set_game_view(False)
except Exception:
    pass

try:
    unreal.EditorLevelLibrary.save_current_level()
except Exception:
    try:
        level_sub.save_current_level()
    except Exception:
        pass

unreal.log('BUILD 1.3.1 COMPLETE: Lifted B13 visitor center by %.1f and created podium under group.' % LIFT_Z)
