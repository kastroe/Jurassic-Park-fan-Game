import unreal

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assetlib = unreal.EditorAssetLibrary

# ============================================================
# BUILD 1.4 — VISITOR CENTER SCALE + SEAT FIX
#
# The zoomed-out screenshot shows the actual problem:
# the B13 Visitor Center is not mainly "buried" — it is much too
# small relative to the island/map.  This pass:
#   1) enlarges the whole B13 Visitor Center as ONE group
#   2) preserves its proportions
#   3) keeps it on one shared base height
#   4) creates a larger matching podium under it
#
# No manual moving/scaling required.
# ============================================================

PREFIX = "B13_JP_VC_"
HELPER_PREFIX = "B14_JP_VC_"

# Overall enlargement.
XY_SCALE = 3.25
Z_SCALE  = 1.65

# Small final lift so the floor/steps are clearly above the podium.
FINAL_LIFT = 90.0

# Pivot/anchor = intended Visitor Center centre.
PIVOT_X = -10080.0
PIVOT_Y = -3024.0

cube = assetlib.load_asset("/Engine/BasicShapes/Cube.Cube")

MAT_DIR = "/Game/JPGenerated/Materials"
def load_mat(name):
    p = MAT_DIR + "/" + name
    return assetlib.load_asset(p) if assetlib.does_asset_exist(p) else None

M_STONE = load_mat("M_JP_Stone")
M_CONCRETE = load_mat("M_JP_Concrete")
M_PODIUM = M_STONE if M_STONE else M_CONCRETE

def by_prefix(prefix):
    return [a for a in actor_sub.get_all_level_actors()
            if a.get_actor_label().startswith(prefix)]

# Delete only previous 1.4 helpers.
for a in list(by_prefix(HELPER_PREFIX)):
    actor_sub.destroy_actor(a)

vc = by_prefix(PREFIX)
if not vc:
    unreal.log_error("BUILD 1.4: no B13_JP_VC_ actors found.")
    raise RuntimeError("Run Build 1.3 first.")

# Undo the previous 1.3.1 helper podium if present, so we don't stack podiums.
for a in list(actor_sub.get_all_level_actors()):
    if a.get_actor_label() in ("B131_JP_VC_Podium", "B131_JP_VC_PodiumCap"):
        actor_sub.destroy_actor(a)

# ------------------------------------------------------------
# Compute group base before transforming.
# ------------------------------------------------------------
min_z = 10**18
for a in vc:
    origin, extent = a.get_actor_bounds(False)
    min_z = min(min_z, origin.z - extent.z)

# ------------------------------------------------------------
# Scale each actor around one common pivot.
# Positions are expanded horizontally; heights are expanded relative
# to the group's lowest point, so the whole building remains unified.
# ------------------------------------------------------------
for a in vc:
    loc = a.get_actor_location()
    scale = a.get_actor_scale3d()

    rel_x = loc.x - PIVOT_X
    rel_y = loc.y - PIVOT_Y
    rel_z = loc.z - min_z

    new_loc = unreal.Vector(
        PIVOT_X + rel_x * XY_SCALE,
        PIVOT_Y + rel_y * XY_SCALE,
        min_z + rel_z * Z_SCALE + FINAL_LIFT
    )

    new_scale = unreal.Vector(
        scale.x * XY_SCALE,
        scale.y * XY_SCALE,
        scale.z * Z_SCALE
    )

    a.set_actor_location(new_loc, False, False)
    a.set_actor_scale3d(new_scale)

# ------------------------------------------------------------
# Build a properly sized podium beneath the transformed group.
# ------------------------------------------------------------
new_min_x = new_min_y = new_min_z = 10**18
new_max_x = new_max_y = new_max_z = -10**18

for a in vc:
    origin, extent = a.get_actor_bounds(False)
    new_min_x = min(new_min_x, origin.x - extent.x)
    new_max_x = max(new_max_x, origin.x + extent.x)
    new_min_y = min(new_min_y, origin.y - extent.y)
    new_max_y = max(new_max_y, origin.y + extent.y)
    new_min_z = min(new_min_z, origin.z - extent.z)
    new_max_z = max(new_max_z, origin.z + extent.z)

margin = 550.0
podium_thickness = 65.0

width_x = (new_max_x - new_min_x) + margin*2
width_y = (new_max_y - new_min_y) + margin*2
center_x = (new_min_x + new_max_x)/2
center_y = (new_min_y + new_max_y)/2
podium_z = new_min_z - podium_thickness/2 - 5.0

podium = actor_sub.spawn_actor_from_class(
    unreal.StaticMeshActor,
    unreal.Vector(center_x, center_y, podium_z),
    unreal.Rotator(0,0,0)
)
podium.set_actor_label("B14_JP_VC_Podium")
podium.static_mesh_component.set_static_mesh(cube)
if M_PODIUM:
    podium.static_mesh_component.set_material(0, M_PODIUM)
podium.set_actor_scale3d(
    unreal.Vector(width_x/100.0, width_y/100.0, podium_thickness/100.0)
)

# ------------------------------------------------------------
# Save.
# ------------------------------------------------------------
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    unreal.EditorLevelLibrary.save_current_level()

unreal.log(
    "JP BUILD 1.4 COMPLETE: Visitor Center enlarged %.2fx XY / %.2fx Z and reseated; actors=%d"
    % (XY_SCALE, Z_SCALE, len(vc))
)
