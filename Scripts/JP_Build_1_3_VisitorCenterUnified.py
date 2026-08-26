import unreal

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assetlib = unreal.EditorAssetLibrary

# ============================================================
# BUILD 1.3 — UNIFIED VISITOR CENTER
# Fixes the problem where the Visitor Center parts were spread
# across uneven terrain / buried / not reading as one building.
#
# This version deliberately uses ONE shared base Z for the whole
# Visitor Center, exactly like the gate build reads as one object.
# ============================================================

cube = assetlib.load_asset("/Engine/BasicShapes/Cube.Cube")
cyl  = assetlib.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
cone = assetlib.load_asset("/Engine/BasicShapes/Cone.Cone")

MAT_DIR = "/Game/JPGenerated/Materials"
def mat(name):
    p = MAT_DIR + "/" + name
    return assetlib.load_asset(p) if assetlib.does_asset_exist(p) else None

M_CONCRETE = mat("M_JP_Concrete")
M_STONE    = mat("M_JP_Stone")
M_ASPHALT  = mat("M_JP_Asphalt")
M_ROOF     = mat("M_JP_ThatchApprox")
M_WOOD     = mat("M_JP_DarkWood")
M_GLASS    = mat("M_JP_GlassDark")
M_GATE     = mat("M_JP_GateDark")

def by_prefix(prefix):
    return [a for a in actor_sub.get_all_level_actors()
            if a.get_actor_label().startswith(prefix)]

def set_mat(a, m):
    if not m:
        return
    try:
        a.static_mesh_component.set_material(0, m)
    except Exception:
        pass

def spawn(label, mesh, x, y, z, sx, sy, sz, material=None, yaw=0.0):
    a = actor_sub.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(x, y, z),
        unreal.Rotator(0.0, yaw, 0.0)
    )
    a.set_actor_label(label)
    a.static_mesh_component.set_static_mesh(mesh)
    a.set_actor_scale3d(unreal.Vector(sx, sy, sz))
    set_mat(a, material)
    return a

# Clean previous 1.3.
for a in list(by_prefix("B13_JP_VC_")):
    actor_sub.destroy_actor(a)

# Hide every earlier Visitor Center version, but leave the gate alone.
for a in actor_sub.get_all_level_actors():
    n = a.get_actor_label()
    if (
        n.startswith("B06_JP_VisitorCenter_") or
        n.startswith("B08_JP_VC_") or
        n.startswith("B09_JP_VC_") or
        n.startswith("B10_JP_VC_") or
        n.startswith("B11_JP_VC_") or
        n.startswith("B12_JP_VC_")
    ):
        try:
            a.set_is_temporarily_hidden_in_editor(True)
        except Exception:
            pass

# ------------------------------------------------------------
# FIXED LANDMARK TRANSFORM
# ------------------------------------------------------------
# Same Visitor Center X/Y used by previous builds.
VCX = -10080.0
VCY = -3024.0

# Use the visible 1.1/1.2 terrace if present to infer the actual local Z,
# otherwise fall back to the known Build 0.5 Visitor Center elevation.
BASE_Z = 3324.0

for candidate in actor_sub.get_all_level_actors():
    n = candidate.get_actor_label()
    if n in ("B12_JP_VC_Terrace", "B11_JP_VC_Terrace", "B10_JP_VC_Terrace"):
        try:
            p = candidate.get_actor_location()
            # Those terrace slabs are thin, so their center is close to ground.
            if -20000.0 < p.z < 30000.0:
                BASE_Z = p.z - 10.0
                break
        except Exception:
            pass

# Everything below is built from this ONE BASE_Z.
# This is the core fix.

def rel(label, mesh, dx, dy, dz, sx, sy, sz, material=None, yaw=0.0):
    return spawn(
        label, mesh,
        VCX + dx, VCY + dy, BASE_Z + dz,
        sx, sy, sz, material, yaw
    )

# ============================================================
# TERRACE / FRONT APPROACH
# ============================================================
rel("B13_JP_VC_Terrace", cube, -650, 0, 22, 60, 45, 0.22, M_STONE)
rel("B13_JP_VC_Forecourt", cube, -5600, 0, 18, 31, 14, 0.10, M_ASPHALT)

# ============================================================
# THREE PAVILION BUILDING
# Reference target:
#   small side pavilion — large central pavilion — small side pavilion
# all visually connected and wide/low.
# ============================================================

# CENTRAL BODY
CX = 500.0
rel("B13_JP_VC_CentralBody", cyl, CX, 0, 260, 21.5, 21.5, 5.0, M_CONCRETE)
rel("B13_JP_VC_CentralGlassBand", cyl, CX, 0, 505, 21.8, 21.8, 0.55, M_GLASS)

# broad, low central roof
rel("B13_JP_VC_CentralRoof", cone, CX, 0, 835, 27.0, 27.0, 3.2, M_ROOF)
rel("B13_JP_VC_CentralEave", cyl, CX, 0, 680, 27.3, 27.3, 0.30, M_GATE)

# central upper cupola
rel("B13_JP_VC_CupolaBody", cyl, CX, 0, 1030, 6.8, 6.8, 1.7, M_CONCRETE)
rel("B13_JP_VC_CupolaRoof", cone, CX, 0, 1215, 8.2, 8.2, 2.2, M_ROOF)

# SIDE PAVILIONS
for side, dy in (("L", -3500.0), ("R", 3500.0)):
    rel("B13_JP_VC_SideBody_" + side, cyl, 900, dy, 225, 14.8, 14.8, 4.3, M_CONCRETE)
    rel("B13_JP_VC_SideGlass_" + side, cyl, 900, dy, 425, 15.0, 15.0, 0.45, M_GLASS)
    rel("B13_JP_VC_SideRoof_" + side, cone, 900, dy, 710, 18.6, 18.6, 3.0, M_ROOF)
    rel("B13_JP_VC_SideEave_" + side, cyl, 900, dy, 575, 18.9, 18.9, 0.26, M_GATE)
    rel("B13_JP_VC_SideCupola_" + side, cone, 900, dy, 900, 5.3, 5.3, 1.8, M_ROOF)

# CONNECTORS: deliberately overlap both central and side pavilions.
rel("B13_JP_VC_Connector_L", cube, 450, -2050, 235, 24, 10, 4.2, M_CONCRETE, -8)
rel("B13_JP_VC_Connector_R", cube, 450,  2050, 235, 24, 10, 4.2, M_CONCRETE,  8)

# ============================================================
# FRONT FACADE / ENTRY
# ============================================================
ENTRY_X = -2450.0

# projecting entrance tower
rel("B13_JP_VC_EntranceBlock", cube, ENTRY_X, 0, 300, 8.5, 11.5, 6.0, M_STONE)

# wooden door
rel("B13_JP_VC_Door", cube, ENTRY_X - 455, 0, 245, 0.55, 4.7, 4.8, M_WOOD)

# stone doorway frame
for side, dy in (("L", -470), ("R", 470)):
    rel("B13_JP_VC_DoorPier_" + side, cube, ENTRY_X - 500, dy, 280, 0.75, 0.75, 5.6, M_STONE)
rel("B13_JP_VC_DoorLintel", cube, ENTRY_X - 500, 0, 575, 0.8, 10.8, 0.75, M_STONE)

# windows + columns across curved-looking facade
for i, dy in enumerate((-1500,-1050,-600,600,1050,1500)):
    rel("B13_JP_VC_Window_%02d" % i, cube, -1450, dy, 255, 0.18, 3.4, 3.6, M_GLASS)

for i, dy in enumerate((-1750,-1300,-850,-400,400,850,1300,1750)):
    rel("B13_JP_VC_Column_%02d" % i, cyl, -1570, dy, 250, 0.36, 0.36, 5.0, M_CONCRETE)

# ============================================================
# STAIRS / PLANTER WALLS
# ============================================================
for i in range(11):
    # stairs move forward toward road and get wider toward bottom
    dx = -3150 - i*175
    width = 13.0 + i*1.05
    rel("B13_JP_VC_Stair_%02d" % i, cube, dx, 0, 18 + i*9, width, 0.88, 0.18, M_CONCRETE)

rel("B13_JP_VC_Planter_L", cube, -3800, -1450, 95, 17.5, 2.2, 1.35, M_CONCRETE, -16)
rel("B13_JP_VC_Planter_R", cube, -3800,  1450, 95, 17.5, 2.2, 1.35, M_CONCRETE,  16)

# Save current level.
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    unreal.EditorLevelLibrary.save_current_level()

unreal.log(
    "JP BUILD 1.3 COMPLETE: unified Visitor Center; base_z=%.1f; created=%d"
    % (BASE_Z, len(by_prefix("B13_JP_VC_")))
)
