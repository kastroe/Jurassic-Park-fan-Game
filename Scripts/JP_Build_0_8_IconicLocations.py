import unreal, os, struct, zlib, math, random

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assetlib = unreal.EditorAssetLibrary

PROJECT = unreal.Paths.project_dir()
HEIGHTMAP = os.path.join(PROJECT, "Content", "JPBlockout", "JP_Island_Heightmap_2017_v05.png")

if not os.path.exists(HEIGHTMAP):
    raise RuntimeError("Missing Build 0.5 heightmap: " + HEIGHTMAP)

# ============================================================
# BUILD 0.8 — ICONIC LOCATIONS PASS
# Builds on 0.7 and uses only built-in Unreal geometry/materials.
# ============================================================

# ------------------------
# Heightmap reader
# ------------------------
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
                raise RuntimeError("Expected 16-bit grayscale non-interlaced PNG.")
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
MINX=MINY=-100800.0
PER=100.0

def terrain_z(x,y):
    fx=max(0.0,min(W-1.001,(x-MINX)/PER))
    fy=max(0.0,min(H-1.001,(y-MINY)/PER))
    x0=int(fx); y0=int(fy)
    x1=min(W-1,x0+1); y1=min(H-1,y0+1)
    tx=fx-x0; ty=fy-y0

    v=(
        HM[y0][x0]*(1-tx)*(1-ty)
        + HM[y0][x1]*tx*(1-ty)
        + HM[y1][x0]*(1-tx)*ty
        + HM[y1][x1]*tx*ty
    )
    return (float(v)-32768.0)*100.0/128.0

# ------------------------
# Basic meshes/materials
# ------------------------
cube   = assetlib.load_asset("/Engine/BasicShapes/Cube.Cube")
cyl    = assetlib.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
cone   = assetlib.load_asset("/Engine/BasicShapes/Cone.Cone")
sphere = assetlib.load_asset("/Engine/BasicShapes/Sphere.Sphere")

if not all([cube,cyl,cone,sphere]):
    raise RuntimeError("Could not load Unreal basic shape meshes.")

MAT_DIR="/Game/JPGenerated/Materials"

def mat(name):
    path=MAT_DIR+"/"+name
    if not assetlib.does_asset_exist(path):
        raise RuntimeError("Missing Build 0.7 material: "+path)
    return assetlib.load_asset(path)

M_ASPHALT = mat("M_JP_Asphalt")
M_CONCRETE = mat("M_JP_Concrete")
M_STONE = mat("M_JP_Stone")
M_GATE = mat("M_JP_GateDark")
M_RED = mat("M_JP_RoofRed")
M_METAL = mat("M_JP_FenceMetal")
M_GRASS = mat("M_JP_Grass")
M_LEAF = mat("M_JP_Leaf")
M_TRUNK = mat("M_JP_Trunk")

def actors_by_prefix(prefix):
    return [a for a in actor_sub.get_all_level_actors() if a.get_actor_label().startswith(prefix)]

# Clean previous 0.8 run.
for a in list(actors_by_prefix("B08_JP_")):
    actor_sub.destroy_actor(a)

def apply_mat(actor, material):
    try:
        actor.static_mesh_component.set_material(0,material)
    except Exception:
        pass

def spawn(label, mesh, x,y,z,sx,sy,sz,material=None,yaw=0,pitch=0,roll=0):
    a=actor_sub.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(x,y,z),
        unreal.Rotator(pitch,yaw,roll)
    )
    a.set_actor_label(label)
    a.static_mesh_component.set_static_mesh(mesh)
    a.set_actor_scale3d(unreal.Vector(sx,sy,sz))
    if material:
        apply_mat(a,material)
    return a

def ground(label,mesh,x,y,sx,sy,sz,material=None,extra=0,yaw=0,pitch=0,roll=0):
    return spawn(
        label,mesh,x,y,
        terrain_z(x,y)+(sz*50.0)+extra,
        sx,sy,sz,material,yaw,pitch,roll
    )

# Known landmark centers.
VC=(-10080.0,-3024.0)
GATE=(2016.0,2016.0)
RAPTOR=(-18144.0,-12096.0)
HELIPAD=(-66528.0,-63504.0)
DILO=(22176.0,-10080.0)
TRIKE=(33264.0,3024.0)
TREX=(45360.0,6048.0)

# ============================================================
# 1) VISITOR CENTER — stronger 1993 silhouette
# ============================================================
vcx,vcy=VC
vcz=terrain_z(vcx,vcy)

# Raised circular rotunda base and layered roof.
ground("B08_JP_VC_Rotunda_Base",cyl,vcx-1800,vcy,17,17,1.5,M_STONE,20)
spawn("B08_JP_VC_Rotunda_Mid",cyl,vcx-1800,vcy,vcz+650,13.5,13.5,5.0,M_CONCRETE)
spawn("B08_JP_VC_Rotunda_Roof",cone,vcx-1800,vcy,vcz+1280,17.5,17.5,4.0,M_RED)

# Front portico / entrance.
ground("B08_JP_VC_Portico",cube,vcx-3450,vcy,14,18,0.75,M_CONCRETE,110)
for side,dy in [("L",-720),("R",720)]:
    ground("B08_JP_VC_Portico_Column_"+side,cyl,vcx-3650,vcy+dy,0.7,0.7,7.0,M_STONE,0)

# Rear building massing.
ground("B08_JP_VC_BackBlock",cube,vcx+1700,vcy,38,25,7.0,M_CONCRETE,10)

# Wing buildings.
for side,dy,yaw in [("L",-2450,-18),("R",2450,18)]:
    ground("B08_JP_VC_Wing_"+side,cube,vcx+400,vcy+dy,27,8,4.7,M_STONE,10,yaw=yaw)
    # roof strip
    spawn("B08_JP_VC_WingRoof_"+side,cube,
          vcx+400,vcy+dy,
          terrain_z(vcx+400,vcy+dy)+520,
          27.5,8.5,0.55,M_RED,yaw=yaw)

# Forecourt loop pieces.
for i,(dx,dy,sx,sy,yaw) in enumerate([
    (-4700,0,18,45,0),
    (-3900,-3000,34,7,-28),
    (-3900,3000,34,7,28),
]):
    ground(f"B08_JP_VC_Drive_{i}",cube,vcx+dx,vcy+dy,sx,sy,0.10,M_ASPHALT,12,yaw=yaw)

# Decorative low stone walls near entrance.
for side,dy in [("L",-1250),("R",1250)]:
    ground("B08_JP_VC_LowWall_"+side,cube,vcx-4100,vcy+dy,13,1.2,1.1,M_STONE,0)

# ============================================================
# 2) TOUR GATES — iconic silhouette and road approach
# ============================================================
gx,gy=GATE
gz=terrain_z(gx,gy)

# Wider towers.
for side,dy in [("L",-1100),("R",1100)]:
    ground("B08_JP_GATE_Tower_"+side,cube,gx,gy+dy,3.8,3.8,18,M_GATE)
    # red cap block
    spawn("B08_JP_GATE_Cap_"+side,cube,gx,gy+dy,gz+1950,4.2,4.2,1.2,M_RED)

# Crossbeam.
spawn("B08_JP_GATE_MainBeam",cube,gx,gy,gz+1850,3.5,27,2.1,M_GATE)

# Triangular/stepped crest using several pieces.
spawn("B08_JP_GATE_CrestCenter",cube,gx-50,gy,gz+2260,3.0,11,0.85,M_RED)
spawn("B08_JP_GATE_CrestL",cube,gx-80,gy-900,gz+2180,3.0,9,0.75,M_GATE,yaw=-10)
spawn("B08_JP_GATE_CrestR",cube,gx-80,gy+900,gz+2180,3.0,9,0.75,M_GATE,yaw=10)

# Approach road widened in front/behind gates.
ground("B08_JP_GATE_Approach_A",cube,gx-3200,gy,38,10,0.11,M_ASPHALT,12)
ground("B08_JP_GATE_Approach_B",cube,gx+3200,gy,38,10,0.11,M_ASPHALT,12)

# Gate side marker posts.
for side,dy in [("L",-2050),("R",2050)]:
    ground("B08_JP_GATE_SidePost_"+side,cube,gx,gy+dy,0.7,0.7,8,M_METAL)

# ============================================================
# 3) ROAD EDGES / CURBS
# ============================================================
route_points=[
    (-66528,-63504),
    (-40320,-22176),
    (-10080,-3024),
    (2016,2016),
    (22176,-10080),
    (33264,3024),
    (45360,6048),
]

def segment_offset(ax,ay,bx,by,offset):
    dx,dy=bx-ax,by-ay
    d=max(1.0,math.sqrt(dx*dx+dy*dy))
    nx=-dy/d; ny=dx/d
    return (nx*offset,ny*offset)

def add_road_edge(prefix,a,b,width=900,seglen=1800):
    ax,ay=a; bx,by=b
    dx,dy=bx-ax,by-ay
    dist=math.sqrt(dx*dx+dy*dy)
    count=max(1,int(math.ceil(dist/seglen)))
    yaw=math.degrees(math.atan2(dy,dx))
    ox,oy=segment_offset(ax,ay,bx,by,width/2+90)

    for i in range(count):
        t=(i+0.5)/count
        x=ax+dx*t; y=ay+dy*t
        seg=dist/count

        for side,sgn in [("L",1),("R",-1)]:
            xx=x+ox*sgn; yy=y+oy*sgn
            ground(
                f"B08_JP_CURB_{prefix}_{side}_{i:02d}",
                cube,xx,yy,
                seg/100.0,0.22,0.20,
                M_CONCRETE,12,yaw=yaw
            )

for i,(a,b) in enumerate(zip(route_points,route_points[1:])):
    add_road_edge(str(i),a,b,900 if i<2 else 700)

# ============================================================
# 4) BETTER PADDOCK FENCE — tall electric style
# ============================================================
def fence_loop(name,cx,cy,rx,ry,segments):
    pts=[]
    for i in range(segments):
        ang=2*math.pi*i/segments
        pts.append((cx+math.cos(ang)*rx,cy+math.sin(ang)*ry))

    for i,(x,y) in enumerate(pts):
        z=terrain_z(x,y)

        # substantial tall post
        spawn(
            f"B08_JP_FENCE_{name}_POST_{i:02d}",
            cube,x,y,z+450,
            0.28,0.28,9.0,M_METAL
        )

        x2,y2=pts[(i+1)%segments]
        dx,dy=x2-x,y2-y
        dist=math.sqrt(dx*dx+dy*dy)
        yaw=math.degrees(math.atan2(dy,dx))
        xm,ym=(x+x2)/2,(y+y2)/2
        zm=terrain_z(xm,ym)

        # five horizontal wires/rails.
        for idx,h in enumerate([130,290,450,610,770]):
            spawn(
                f"B08_JP_FENCE_{name}_WIRE_{i:02d}_{idx}",
                cube,xm,ym,zm+h,
                dist/100.0,0.045,0.045,M_METAL,yaw=yaw
            )

fence_loop("DILO",DILO[0],DILO[1],6400,4900,34)
fence_loop("TRIKE",TRIKE[0],TRIKE[1],6700,5300,36)
fence_loop("TREX",TREX[0],TREX[1],7800,5800,40)

# Hide older Build 0.6 fence so 0.8 becomes the visible fence.
for a in actor_sub.get_all_level_actors():
    if a.get_actor_label().startswith("B06_JP_FENCE_"):
        try:
            a.set_is_temporarily_hidden_in_editor(True)
        except Exception:
            pass

# ============================================================
# 5) RAPTOR PEN DETAIL
# ============================================================
rx,ry=RAPTOR
rz=terrain_z(rx,ry)

ground("B08_JP_RAPTOR_Base",cyl,rx,ry,12.5,12.5,1.2,M_CONCRETE,10)

# high perimeter posts + upper ring-ish rails
rad=1500
pts=[]
for i in range(12):
    ang=2*math.pi*i/12
    x=rx+math.cos(ang)*rad
    y=ry+math.sin(ang)*rad
    pts.append((x,y))
    ground(f"B08_JP_RAPTOR_Post_{i:02d}",cube,x,y,0.45,0.45,11,M_METAL)

for i,(x,y) in enumerate(pts):
    x2,y2=pts[(i+1)%len(pts)]
    dx,dy=x2-x,y2-y
    d=math.sqrt(dx*dx+dy*dy)
    yaw=math.degrees(math.atan2(dy,dx))
    xm,ym=(x+x2)/2,(y+y2)/2
    spawn(f"B08_JP_RAPTOR_Rail_{i:02d}",cube,xm,ym,terrain_z(xm,ym)+900,
          d/100.0,0.11,0.11,M_METAL,yaw=yaw)

# crane mast + boom
ground("B08_JP_RAPTOR_CraneMast",cube,rx+1900,ry,0.7,0.7,17,M_METAL)
spawn("B08_JP_RAPTOR_CraneBoom",cube,rx+900,ry,rz+1700,22,0.45,0.45,M_METAL)

# ============================================================
# 6) DENSER JUNGLE ALONG TOUR CORRIDOR
# ============================================================
random.seed(199306)

def point_seg_dist(px,py,ax,ay,bx,by):
    vx,vy=bx-ax,by-ay
    wx,wy=px-ax,py-ay
    vv=vx*vx+vy*vy
    if vv<=0:return math.sqrt(wx*wx+wy*wy)
    t=max(0,min(1,(wx*vx+wy*vy)/vv))
    qx=ax+t*vx; qy=ay+t*vy
    return math.sqrt((px-qx)**2+(py-qy)**2)

# create vegetation mainly 2.5m–10m from route, not ON road
tree_index=0
for seg_i,(a,b) in enumerate(zip(route_points,route_points[1:])):
    ax,ay=a; bx,by=b
    dx,dy=bx-ax,by-ay
    dist=math.sqrt(dx*dx+dy*dy)
    count=max(12,int(dist/1700))

    for i in range(count):
        t=(i+random.random())/count
        cx=ax+dx*t
        cy=ay+dy*t

        for side in (-1,1):
            if random.random()>0.82:
                continue
            d=max(1.0,dist)
            nx=-dy/d; ny=dx/d
            offset=random.uniform(2600,7200)*side
            x=cx+nx*offset+random.uniform(-700,700)
            y=cy+ny*offset+random.uniform(-700,700)
            z=terrain_z(x,y)

            if z < 700:
                continue

            trunk_h=random.uniform(550,950)
            canopy=random.uniform(6.0,10.5)

            spawn(
                f"B08_JP_ROUTE_TREE_{tree_index:03d}_Trunk",
                cyl,x,y,z+trunk_h/2,
                0.7,0.7,trunk_h/100,M_TRUNK
            )
            spawn(
                f"B08_JP_ROUTE_TREE_{tree_index:03d}_Canopy",
                cone,x,y,z+trunk_h+320,
                canopy,canopy,7.0,M_LEAF,
                yaw=random.uniform(0,360)
            )
            tree_index+=1

# ============================================================
# 7) ENTRY / HELIPAD LANDSCAPING
# ============================================================
hx,hy=HELIPAD
for i in range(18):
    ang=2*math.pi*i/18
    r=random.uniform(1800,3200)
    x=hx+math.cos(ang)*r
    y=hy+math.sin(ang)*r
    z=terrain_z(x,y)
    th=random.uniform(500,800)
    spawn(f"B08_JP_HELIPAD_TREE_{i}_Trunk",cyl,x,y,z+th/2,0.65,0.65,th/100,M_TRUNK)
    spawn(f"B08_JP_HELIPAD_TREE_{i}_Canopy",cone,x,y,z+th+280,7,7,6,M_LEAF,yaw=i*20)

# ============================================================
# SAVE
# ============================================================
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    unreal.EditorLevelLibrary.save_current_level()

unreal.log(
    "JP BUILD 0.8 COMPLETE: iconic locations built; route trees=%d; visual actors=%d"
    % (tree_index, len(actors_by_prefix("B08_JP_")))
)
