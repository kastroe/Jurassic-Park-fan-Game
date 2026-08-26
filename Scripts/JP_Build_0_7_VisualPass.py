import unreal, os, struct, zlib, math, random

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
matlib = unreal.MaterialEditingLibrary
assetlib = unreal.EditorAssetLibrary

PROJECT = unreal.Paths.project_dir()
HEIGHTMAP = os.path.join(PROJECT, "Content", "JPBlockout", "JP_Island_Heightmap_2017_v05.png")

if not os.path.exists(HEIGHTMAP):
    raise RuntimeError("Missing Build 0.5 heightmap: " + HEIGHTMAP)

# ============================================================
# HEIGHTMAP READER
# ============================================================
def read_png16_gray(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("Heightmap is not a PNG.")

    pos = 8
    idat = bytearray()
    width = height = None

    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos+4])[0]
        typ = data[pos+4:pos+8]
        chunk = data[pos+8:pos+8+ln]
        pos += 12 + ln

        if typ == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
            if bit_depth != 16 or color_type != 0 or interlace != 0:
                raise RuntimeError("Expected non-interlaced 16-bit grayscale PNG.")
        elif typ == b"IDAT":
            idat.extend(chunk)
        elif typ == b"IEND":
            break

    raw = zlib.decompress(bytes(idat))
    stride = width * 2
    prev = bytearray(stride)
    rows = []
    p = 0

    def paeth(a,b,c):
        q = a+b-c
        pa,pb,pc = abs(q-a),abs(q-b),abs(q-c)
        return a if pa<=pb and pa<=pc else (b if pb<=pc else c)

    for _ in range(height):
        ft = raw[p]; p += 1
        scan = bytearray(raw[p:p+stride]); p += stride
        recon = bytearray(stride)

        for i in range(stride):
            x=scan[i]
            a=recon[i-2] if i>=2 else 0
            b=prev[i]
            c=prev[i-2] if i>=2 else 0
            if ft==0: v=x
            elif ft==1: v=(x+a)&255
            elif ft==2: v=(x+b)&255
            elif ft==3: v=(x+((a+b)//2))&255
            elif ft==4: v=(x+paeth(a,b,c))&255
            else: raise RuntimeError("Unsupported PNG filter.")
            recon[i]=v

        rows.append([(recon[i]<<8)|recon[i+1] for i in range(0,stride,2)])
        prev=recon

    return width,height,rows

W,H,HM = read_png16_gray(HEIGHTMAP)
MINX = MINY = -100800.0
PER = 100.0

def terrain_z(x,y):
    fx=max(0.0,min(W-1.001,(x-MINX)/PER))
    fy=max(0.0,min(H-1.001,(y-MINY)/PER))
    x0=int(fx); y0=int(fy)
    x1=min(W-1,x0+1); y1=min(H-1,y0+1)
    tx=fx-x0; ty=fy-y0
    v=(HM[y0][x0]*(1-tx)*(1-ty)+HM[y0][x1]*tx*(1-ty)+
       HM[y1][x0]*(1-tx)*ty+HM[y1][x1]*tx*ty)
    return (float(v)-32768.0)*100.0/128.0

# ============================================================
# MATERIAL CREATION
# ============================================================
MAT_DIR = "/Game/JPGenerated/Materials"
if not assetlib.does_directory_exist(MAT_DIR):
    assetlib.make_directory(MAT_DIR)

def make_material(name, rgb, rough=0.7, metallic=0.0):
    path = MAT_DIR + "/" + name
    if assetlib.does_asset_exist(path):
        return assetlib.load_asset(path)

    mat = asset_tools.create_asset(name, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    if not mat:
        raise RuntimeError("Could not create material: " + name)

    color = matlib.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -350, -80)
    color.constant = unreal.LinearColor(rgb[0],rgb[1],rgb[2],1.0)
    matlib.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)

    r = matlib.create_material_expression(mat, unreal.MaterialExpressionConstant, -350, 40)
    r.r = rough
    matlib.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)

    m = matlib.create_material_expression(mat, unreal.MaterialExpressionConstant, -350, 140)
    m.r = metallic
    matlib.connect_material_property(m, "", unreal.MaterialProperty.MP_METALLIC)

    matlib.recompile_material(mat)
    assetlib.save_asset(path, only_if_is_dirty=False)
    return mat

materials = {
    "asphalt": make_material("M_JP_Asphalt", (0.035,0.040,0.045), 0.88, 0.0),
    "concrete": make_material("M_JP_Concrete", (0.36,0.34,0.29), 0.82, 0.0),
    "stone": make_material("M_JP_Stone", (0.17,0.16,0.13), 0.90, 0.0),
    "gate": make_material("M_JP_GateDark", (0.055,0.035,0.020), 0.78, 0.1),
    "red": make_material("M_JP_RoofRed", (0.24,0.025,0.018), 0.70, 0.0),
    "metal": make_material("M_JP_FenceMetal", (0.09,0.10,0.095), 0.48, 0.75),
    "grass": make_material("M_JP_Grass", (0.035,0.12,0.028), 0.97, 0.0),
    "leaf": make_material("M_JP_Leaf", (0.018,0.095,0.022), 0.94, 0.0),
    "trunk": make_material("M_JP_Trunk", (0.12,0.055,0.018), 0.93, 0.0),
    "water": make_material("M_JP_WaterBlockout", (0.015,0.06,0.12), 0.20, 0.05),
}

# ============================================================
# BASIC ASSETS
# ============================================================
cube = assetlib.load_asset("/Engine/BasicShapes/Cube.Cube")
cyl  = assetlib.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
cone = assetlib.load_asset("/Engine/BasicShapes/Cone.Cone")
sphere = assetlib.load_asset("/Engine/BasicShapes/Sphere.Sphere")

if not all([cube,cyl,cone,sphere]):
    raise RuntimeError("Could not load Unreal basic shape assets.")

def by_prefix(prefix):
    return [a for a in actor_sub.get_all_level_actors()
            if a.get_actor_label().startswith(prefix)]

def set_mat(actor, material):
    try:
        actor.static_mesh_component.set_material(0, material)
    except Exception:
        pass

# Remove previous 0.7-only visual actors.
for a in list(by_prefix("B07_JP_")):
    actor_sub.destroy_actor(a)

# ============================================================
# MATERIALIZE BUILD 0.6
# ============================================================
for a in actor_sub.get_all_level_actors():
    n=a.get_actor_label()

    if n.startswith("B06_JP_ARRIVAL_ROAD_") or n.startswith("B06_JP_TOUR_ROAD_"):
        set_mat(a, materials["asphalt"])

    elif n.startswith("B06_JP_FENCE_"):
        set_mat(a, materials["metal"])

    elif n.startswith("B06_JP_Gate_"):
        set_mat(a, materials["gate"])

    elif n.startswith("B06_JP_VisitorCenter_"):
        if "Canopy" in n:
            set_mat(a, materials["red"])
        elif "Rotunda" in n:
            set_mat(a, materials["stone"])
        else:
            set_mat(a, materials["concrete"])

    elif n.startswith("B06_JP_RaptorPen_"):
        set_mat(a, materials["metal"])

    elif n.startswith("B06_JP_Maintenance_"):
        set_mat(a, materials["concrete"])

    elif n.startswith("B06_JP_Helipad"):
        set_mat(a, materials["concrete"])

    elif n.startswith("B06_JP_") and "_View" in n:
        set_mat(a, materials["concrete"])

# ============================================================
# WATER/OCEAN BLOCKOUT
# Large flat ocean below the island.
# ============================================================
def spawn_mesh(label, mesh, x,y,z,sx,sy,sz,mat=None,yaw=0):
    a=actor_sub.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(x,y,z),
        unreal.Rotator(0,yaw,0)
    )
    a.set_actor_label(label)
    a.static_mesh_component.set_static_mesh(mesh)
    a.set_actor_scale3d(unreal.Vector(sx,sy,sz))
    if mat:
        set_mat(a,mat)
    return a

spawn_mesh("B07_JP_Ocean_Blockout", cube, 0,0,-1750,
           2700,2700,0.12,materials["water"])

# ============================================================
# GREEN GROUND OVERLAYS
# Thin pads over main gameplay regions. This gives immediate jungle colour
# without requiring a complex Landscape material yet.
# ============================================================
zones=[
    ("VisitorCenter",-10080,-3024,190,160),
    ("BrachioValley",-40320,-22176,240,210),
    ("Dilo",22176,-10080,150,130),
    ("Trike",33264,3024,165,145),
    ("TRex",45360,6048,180,150),
    ("Maintenance",12096,34272,130,110),
    ("Gallimimus",-18144,43344,210,170),
]
for name,x,y,sx,sy in zones:
    z=terrain_z(x,y)+10
    spawn_mesh("B07_JP_Ground_"+name,cube,x,y,z,sx,sy,0.05,materials["grass"])

# ============================================================
# PROCEDURAL JUNGLE PLACEHOLDERS
# Trunk + two cone canopies. Keep clear of major routes/structures.
# ============================================================
random.seed(1993)

avoid = [
    (-10080,-3024,9000),    # Visitor Center
    (-18144,-12096,5000),   # Raptor pen
    (2016,2016,4500),       # Gates
    (-66528,-63504,5000),   # Helipad
    (12096,34272,6000),     # Maintenance
]

road_lines=[
    ((-66528,-63504),(-40320,-22176)),
    ((-40320,-22176),(-10080,-3024)),
    ((-10080,-3024),(2016,2016)),
    ((2016,2016),(22176,-10080)),
    ((22176,-10080),(33264,3024)),
    ((33264,3024),(45360,6048)),
]

def distance_point_segment(px,py,ax,ay,bx,by):
    vx,vy=bx-ax,by-ay
    wx,wy=px-ax,py-ay
    vv=vx*vx+vy*vy
    if vv<=0: return math.sqrt(wx*wx+wy*wy)
    t=max(0,min(1,(wx*vx+wy*vy)/vv))
    qx=ax+t*vx; qy=ay+t*vy
    return math.sqrt((px-qx)**2+(py-qy)**2)

def safe_tree(x,y):
    # Skip sea / extreme coast.
    if terrain_z(x,y) < 600:
        return False
    for ax,ay,r in avoid:
        if (x-ax)**2+(y-ay)**2 < r*r:
            return False
    for (a,b) in road_lines:
        if distance_point_segment(x,y,a[0],a[1],b[0],b[1]) < 1800:
            return False
    return True

tree_count=0
attempts=0
while tree_count < 260 and attempts < 3000:
    attempts += 1
    x=random.uniform(-76000,70000)
    y=random.uniform(-76000,76000)
    if not safe_tree(x,y):
        continue

    z=terrain_z(x,y)
    trunk_h=random.uniform(500,850)
    canopy=random.uniform(5.5,9.5)
    yaw=random.uniform(0,360)

    spawn_mesh(
        "B07_JP_Tree_%03d_Trunk"%tree_count,
        cyl,x,y,z+trunk_h/2,
        0.65,0.65,trunk_h/100,
        materials["trunk"],yaw
    )

    spawn_mesh(
        "B07_JP_Tree_%03d_CanopyA"%tree_count,
        cone,x,y,z+trunk_h+270,
        canopy,canopy,6.0,
        materials["leaf"],yaw
    )

    spawn_mesh(
        "B07_JP_Tree_%03d_CanopyB"%tree_count,
        cone,x+random.uniform(-120,120),y+random.uniform(-120,120),z+trunk_h+500,
        canopy*0.70,canopy*0.70,4.2,
        materials["leaf"],yaw+40
    )
    tree_count += 1

# ============================================================
# VISITOR CENTER DETAIL ACCENTS
# ============================================================
vcx,vcy=-10080,-3024
vcz=terrain_z(vcx,vcy)

# low red roof marker over rotunda/entrance to make the complex identifiable
spawn_mesh("B07_JP_VisitorCenter_RoofAccent",cyl,
           vcx-1800,vcy,vcz+1050,
           16,16,0.55,materials["red"])

# driveway / forecourt
spawn_mesh("B07_JP_VisitorCenter_Forecourt",cube,
           vcx-4300,vcy,terrain_z(vcx-4300,vcy)+12,
           36,28,0.08,materials["asphalt"])

# ============================================================
# HELIPAD H MARK (blockout using white-ish concrete strips)
# ============================================================
hx,hy=-66528,-63504
hz=terrain_z(hx,hy)+55
spawn_mesh("B07_JP_Helipad_H_Left",cube,hx,hy-250,hz,7,0.65,0.08,materials["concrete"])
spawn_mesh("B07_JP_Helipad_H_Right",cube,hx,hy+250,hz,7,0.65,0.08,materials["concrete"])
spawn_mesh("B07_JP_Helipad_H_Cross",cube,hx,hy,hz,0.65,5.5,0.08,materials["concrete"])

# ============================================================
# SAVE
# ============================================================
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    unreal.EditorLevelLibrary.save_current_level()

unreal.log(
    "JP BUILD 0.7 COMPLETE: materials applied, trees=%d, visual actors=%d"
    % (tree_count, len(by_prefix("B07_JP_")))
)
