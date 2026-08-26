import unreal, os, struct, zlib, math

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# ============================================================
# BUILD 0.6 — ENVIRONMENT BLOCKOUT
# Uses only Unreal Engine basic shapes and the Build 0.5 heightmap.
# ============================================================

PROJECT = unreal.Paths.project_dir()
HEIGHTMAP = os.path.join(PROJECT, "Content", "JPBlockout", "JP_Island_Heightmap_2017_v05.png")

if not os.path.exists(HEIGHTMAP):
    raise RuntimeError("Missing Build 0.5 heightmap: " + HEIGHTMAP)

# ------------------------------------------------------------
# Read the exact 16-bit heightmap used for Build 0.5.
# ------------------------------------------------------------
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
        pa, pb, pc = abs(q-a), abs(q-b), abs(q-c)
        return a if pa <= pb and pa <= pc else (b if pb <= pc else c)

    for _ in range(height):
        ft = raw[p]; p += 1
        scan = bytearray(raw[p:p+stride]); p += stride
        recon = bytearray(stride)

        for i in range(stride):
            x = scan[i]
            a = recon[i-2] if i >= 2 else 0
            b = prev[i]
            c = prev[i-2] if i >= 2 else 0

            if ft == 0: v = x
            elif ft == 1: v = (x+a) & 255
            elif ft == 2: v = (x+b) & 255
            elif ft == 3: v = (x+((a+b)//2)) & 255
            elif ft == 4: v = (x+paeth(a,b,c)) & 255
            else: raise RuntimeError("Unsupported PNG filter type %d" % ft)

            recon[i] = v

        rows.append([(recon[i] << 8) | recon[i+1] for i in range(0, stride, 2)])
        prev = recon

    return width, height, rows

W, H, HM = read_png16_gray(HEIGHTMAP)

MINX = MINY = -100800.0
PIXEL = 100.0

def terrain_z(x, y):
    fx = max(0.0, min(W-1.001, (x-MINX)/PIXEL))
    fy = max(0.0, min(H-1.001, (y-MINY)/PIXEL))
    x0 = int(fx); y0 = int(fy)
    x1 = min(W-1, x0+1); y1 = min(H-1, y0+1)
    tx = fx-x0; ty = fy-y0

    v = (
        HM[y0][x0]*(1-tx)*(1-ty) +
        HM[y0][x1]*tx*(1-ty) +
        HM[y1][x0]*(1-tx)*ty +
        HM[y1][x1]*tx*ty
    )
    return (float(v)-32768.0)*100.0/128.0

# ------------------------------------------------------------
# Assets / helpers
# ------------------------------------------------------------
asset_lib = unreal.EditorAssetLibrary
cube = asset_lib.load_asset("/Engine/BasicShapes/Cube.Cube")
cyl  = asset_lib.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")

if not cube or not cyl:
    raise RuntimeError("Could not load Unreal basic shape meshes.")

def by_prefix(prefix):
    return [a for a in actor_sub.get_all_level_actors() if a.get_actor_label().startswith(prefix)]

def by_label(label):
    for a in actor_sub.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None

# Delete only a previous 0.6 run, leaving 0.3/0.5 data intact.
for a in list(by_prefix("B06_JP_")):
    actor_sub.destroy_actor(a)

def spawn_mesh(label, mesh, x, y, z, sx, sy, sz, yaw=0.0):
    a = actor_sub.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(x,y,z),
        unreal.Rotator(0.0,yaw,0.0)
    )
    a.set_actor_label(label)
    a.static_mesh_component.set_static_mesh(mesh)
    a.set_actor_scale3d(unreal.Vector(sx,sy,sz))
    return a

def ground_mesh(label, mesh, x, y, sx, sy, sz, extra=0.0, yaw=0.0):
    # Engine primitives are 100 cm tall before scale.
    z = terrain_z(x,y) + sz*50.0 + extra
    return spawn_mesh(label,mesh,x,y,z,sx,sy,sz,yaw)

# Landmark coordinates retained from Build 0.5.
LM = {
    "Waterfall_Helipad": (-66528.0,-63504.0),
    "Brachiosaurus_Valley": (-40320.0,-22176.0),
    "Visitor_Center": (-10080.0,-3024.0),
    "Raptor_Pen": (-18144.0,-12096.0),
    "Tour_Gates": (2016.0,2016.0),
    "Dilophosaurus_Paddock": (22176.0,-10080.0),
    "Triceratops_Field": (33264.0,3024.0),
    "TRex_Paddock": (45360.0,6048.0),
    "Maintenance_Compound": (12096.0,34272.0),
    "Gallimimus_Plain": (-18144.0,43344.0),
}

# ------------------------------------------------------------
# 1. Proper-looking arrival road + tour road
# ------------------------------------------------------------
def road_segment(prefix, ax, ay, bx, by, width=850.0, seglen=1100.0):
    dx,dy = bx-ax, by-ay
    dist = math.sqrt(dx*dx+dy*dy)
    count = max(1,int(math.ceil(dist/seglen)))
    yaw = math.degrees(math.atan2(dy,dx))

    for i in range(count):
        t0=i/count; t1=(i+1)/count; tm=(t0+t1)/2
        x=ax+dx*tm; y=ay+dy*tm
        length = dist/count
        # Thin road slab, independently terrain-fitted.
        ground_mesh(
            f"B06_JP_{prefix}_{i:03d}",
            cube,x,y,
            length/100.0,width/100.0,0.10,
            extra=10.0,yaw=yaw
        )

def route_between(prefix, names, width):
    for idx,(a,b) in enumerate(zip(names,names[1:])):
        ax,ay=LM[a]; bx,by=LM[b]
        road_segment(f"{prefix}_{idx:02d}_{a}_{b}",ax,ay,bx,by,width,950.0)

route_between("ARRIVAL_ROAD",
              ["Waterfall_Helipad","Brachiosaurus_Valley","Visitor_Center"],
              900.0)

route_between("TOUR_ROAD",
              ["Visitor_Center","Tour_Gates","Dilophosaurus_Paddock","Triceratops_Field","TRex_Paddock"],
              700.0)

# ------------------------------------------------------------
# 2. Visitor Center: stronger movie-style massing
# ------------------------------------------------------------
vcx,vcy = LM["Visitor_Center"]
basez = terrain_z(vcx,vcy)

# main rectangular rear block
ground_mesh("B06_JP_VisitorCenter_Rear",cube,vcx+1800,vcy,38,24,6,extra=20)
# rotunda
ground_mesh("B06_JP_VisitorCenter_Rotunda",cyl,vcx-1800,vcy,15,15,8,extra=20)
# left/right wings
ground_mesh("B06_JP_VisitorCenter_Wing_L",cube,vcx+300,vcy-2100,26,7,4,extra=20,yaw=-18)
ground_mesh("B06_JP_VisitorCenter_Wing_R",cube,vcx+300,vcy+2100,26,7,4,extra=20,yaw=18)
# entrance canopy
ground_mesh("B06_JP_VisitorCenter_Canopy",cube,vcx-3300,vcy,12,18,0.5,extra=140)
# entrance steps
for i in range(4):
    ground_mesh(f"B06_JP_VisitorCenter_Step_{i}",cube,
                vcx-3900-i*260,vcy,
                5.0,18-(i*1.8),0.25,extra=10+i*18)

# ------------------------------------------------------------
# 3. Raptor Pen
# ------------------------------------------------------------
rx,ry = LM["Raptor_Pen"]
# central pen pit / platform
ground_mesh("B06_JP_RaptorPen_Base",cyl,rx,ry,11,11,1.2,extra=10)
# perimeter posts in octagon
radius=1350
for i in range(8):
    ang=math.radians(i*45)
    x=rx+math.cos(ang)*radius
    y=ry+math.sin(ang)*radius
    ground_mesh(f"B06_JP_RaptorPen_Post_{i}",cube,x,y,0.65,0.65,8,extra=0)
# crane-ish mast
ground_mesh("B06_JP_RaptorPen_CraneMast",cube,rx+1650,ry,0.7,0.7,14,extra=0)

# ------------------------------------------------------------
# 4. Jurassic Park tour gates — more substantial
# ------------------------------------------------------------
gx,gy = LM["Tour_Gates"]
pillar_sep=950
left = ground_mesh("B06_JP_Gate_Pillar_L",cube,gx,gy-pillar_sep,2.8,2.8,16,extra=0)
right= ground_mesh("B06_JP_Gate_Pillar_R",cube,gx,gy+pillar_sep,2.8,2.8,16,extra=0)
pillar_top=max(left.get_actor_location().z+800,right.get_actor_location().z+800)
spawn_mesh("B06_JP_Gate_Beam",cube,gx,gy,pillar_top+110,
           2.8,22,2.2,0)
# angled top braces
spawn_mesh("B06_JP_Gate_Top_L",cube,gx-80,gy-550,pillar_top+420,2,8,1.0,-22)
spawn_mesh("B06_JP_Gate_Top_R",cube,gx-80,gy+550,pillar_top+420,2,8,1.0,22)

# ------------------------------------------------------------
# 5. Helipad
# ------------------------------------------------------------
hx,hy=LM["Waterfall_Helipad"]
ground_mesh("B06_JP_Helipad",cyl,hx,hy,12,12,0.35,extra=20)

# ------------------------------------------------------------
# 6. Maintenance compound
# ------------------------------------------------------------
mx,my=LM["Maintenance_Compound"]
ground_mesh("B06_JP_Maintenance_Main",cube,mx,my,23,15,5,extra=10)
ground_mesh("B06_JP_Maintenance_Shed",cube,mx+2600,my-1200,14,9,3.5,extra=10)
ground_mesh("B06_JP_Maintenance_Generator",cube,mx-1800,my+1500,7,5,2.5,extra=10)

# ------------------------------------------------------------
# 7. Paddock fencing
# ------------------------------------------------------------
def fence_ellipse(name,cx,cy,rx,ry,segments=44,height=650.0):
    pts=[]
    for i in range(segments):
        a=2*math.pi*i/segments
        pts.append((cx+math.cos(a)*rx,cy+math.sin(a)*ry))

    for i,(x,y) in enumerate(pts):
        # post
        z=terrain_z(x,y)
        spawn_mesh(f"B06_JP_FENCE_{name}_POST_{i:02d}",cube,
                   x,y,z+height/2,
                   0.20,0.20,height/100.0)

        # rail to next point
        x2,y2=pts[(i+1)%segments]
        dx,dy=x2-x,y2-y
        d=math.sqrt(dx*dx+dy*dy)
        yaw=math.degrees(math.atan2(dy,dx))
        xm,ym=(x+x2)/2,(y+y2)/2
        zm=terrain_z(xm,ym)

        for rail_h in (180,430):
            spawn_mesh(f"B06_JP_FENCE_{name}_RAIL_{i:02d}_{rail_h}",cube,
                       xm,ym,zm+rail_h,
                       d/100.0,0.11,0.11,yaw)

# Approximate movie-area paddocks
dx,dy=LM["Dilophosaurus_Paddock"]
tx,ty=LM["Triceratops_Field"]
rex,rexy=LM["TRex_Paddock"]

fence_ellipse("DILOPHOSAURUS",dx,dy,6200,4700,36)
fence_ellipse("TRICERATOPS",tx,ty,6500,5100,38)
fence_ellipse("TREX",rex,rexy,7600,5600,42)

# ------------------------------------------------------------
# 8. Simple viewing pads / tour pull-offs
# ------------------------------------------------------------
for label,(x,y) in [
    ("Dilo_View", (dx-2700,dy+1100)),
    ("Trike_View",(tx-2400,ty-1000)),
    ("TRex_View",(rex-3100,rexy-1000))
]:
    ground_mesh("B06_JP_"+label,cube,x,y,12,7,0.18,extra=12)

# ------------------------------------------------------------
# 9. Hide old 0.3 graybox geometry (do NOT delete it)
# ------------------------------------------------------------
for a in actor_sub.get_all_level_actors():
    n=a.get_actor_label()
    if n.startswith("GB_JP_"):
        try:
            a.set_is_temporarily_hidden_in_editor(True)
        except Exception:
            pass

# ------------------------------------------------------------
# 10. Save
# ------------------------------------------------------------
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    unreal.EditorLevelLibrary.save_current_level()

created=len(by_prefix("B06_JP_"))
unreal.log("JP BUILD 0.6 COMPLETE: created=%d environment blockout actors" % created)
