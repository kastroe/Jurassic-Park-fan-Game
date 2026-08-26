import unreal, os, struct, zlib, math

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assetlib = unreal.EditorAssetLibrary

PROJECT = unreal.Paths.project_dir()
HEIGHTMAP = os.path.join(PROJECT, "Content", "JPBlockout", "JP_Island_Heightmap_2017_v05.png")

if not os.path.exists(HEIGHTMAP):
    raise RuntimeError("Missing Build 0.5 heightmap: " + HEIGHTMAP)

# ============================================================
# BUILD 0.9 — AUTOMATED CORRECTION PASS
# Corrects Visitor Center + Main Gate automatically.
# The user does NOT need to manually move/scale anything.
# ============================================================

# ------------------------
# Read Build 0.5 heightmap
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
        q=a+b-c
        pa,pb,pc=abs(q-a),abs(q-b),abs(q-c)
        return a if pa<=pb and pa<=pc else (b if pb<=pc else c)

    for _ in range(height):
        ft=raw[p]; p+=1
        scan=bytearray(raw[p:p+stride]); p+=stride
        recon=bytearray(stride)

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
        HM[y0][x0]*(1-tx)*(1-ty) +
        HM[y0][x1]*tx*(1-ty) +
        HM[y1][x0]*(1-tx)*ty +
        HM[y1][x1]*tx*ty
    )
    return (float(v)-32768.0)*100.0/128.0

# ------------------------
# Assets/materials
# ------------------------
cube = assetlib.load_asset("/Engine/BasicShapes/Cube.Cube")
cyl = assetlib.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
cone = assetlib.load_asset("/Engine/BasicShapes/Cone.Cone")

if not all([cube,cyl,cone]):
    raise RuntimeError("Could not load built-in Unreal meshes.")

MAT_DIR="/Game/JPGenerated/Materials"

def get_mat(name):
    p=MAT_DIR+"/"+name
    if not assetlib.does_asset_exist(p):
        raise RuntimeError("Missing Build 0.7 material: "+p)
    return assetlib.load_asset(p)

M_ASPHALT=get_mat("M_JP_Asphalt")
M_CONCRETE=get_mat("M_JP_Concrete")
M_STONE=get_mat("M_JP_Stone")
M_GATE=get_mat("M_JP_GateDark")
M_RED=get_mat("M_JP_RoofRed")
M_METAL=get_mat("M_JP_FenceMetal")

# ------------------------
# Helpers
# ------------------------
def by_prefix(prefix):
    return [a for a in actor_sub.get_all_level_actors()
            if a.get_actor_label().startswith(prefix)]

def set_mat(actor, material):
    try:
        actor.static_mesh_component.set_material(0,material)
    except Exception:
        pass

def spawn(label, mesh, x,y,z,sx,sy,sz, material=None, yaw=0.0, pitch=0.0, roll=0.0):
    a=actor_sub.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(x,y,z),
        unreal.Rotator(pitch,yaw,roll)
    )
    a.set_actor_label(label)
    a.static_mesh_component.set_static_mesh(mesh)
    a.set_actor_scale3d(unreal.Vector(sx,sy,sz))
    if material:
        set_mat(a,material)
    return a

def ground(label,mesh,x,y,sx,sy,sz,material=None,extra=0.0,yaw=0.0,pitch=0.0,roll=0.0):
    z=terrain_z(x,y)+(sz*50.0)+extra
    return spawn(label,mesh,x,y,z,sx,sy,sz,material,yaw,pitch,roll)

# Clean previous 0.9 run.
for a in list(by_prefix("B09_JP_")):
    actor_sub.destroy_actor(a)

# Hide the older 0.8 Visitor Center and gate pieces so the corrected 0.9
# versions become the visible result. Nothing is deleted.
for a in actor_sub.get_all_level_actors():
    n=a.get_actor_label()
    if n.startswith("B08_JP_VC_") or n.startswith("B08_JP_GATE_"):
        try:
            a.set_is_temporarily_hidden_in_editor(True)
        except Exception:
            pass

# ============================================================
# 1) VISITOR CENTER — CORRECTED AUTOMATIC MASSING
# ============================================================
vcx,vcy=-10080.0,-3024.0
vcz=terrain_z(vcx,vcy)

# Large low stone plinth instead of obvious green pad around the building.
ground("B09_JP_VC_Plaza",cyl,vcx-1100,vcy,31,31,0.20,M_STONE,8)

# Rotunda: lower, wider, less like stacked cylinders.
ground("B09_JP_VC_Rotunda_Lower",cyl,vcx-1750,vcy,16.5,16.5,2.0,M_STONE,10)
spawn("B09_JP_VC_Rotunda_Upper",cyl,vcx-1750,vcy,vcz+520,
      13.4,13.4,4.0,M_CONCRETE)
spawn("B09_JP_VC_Rotunda_Roof",cone,vcx-1750,vcy,vcz+980,
      16.2,16.2,2.0,M_RED)

# Thin roof eave to make the roof less cone-like.
spawn("B09_JP_VC_Roof_Eave",cyl,vcx-1750,vcy,vcz+835,
      16.8,16.8,0.32,M_GATE)

# Rear hall moved closer so it connects to rotunda.
ground("B09_JP_VC_RearHall",cube,vcx+1150,vcy,31,21,5.8,M_CONCRETE,10)

# Tapered-ish wings using layered boxes.
for side,dy,yaw in [("L",-2050,-16),("R",2050,16)]:
    ground("B09_JP_VC_Wing_"+side,cube,vcx+250,vcy+dy,
           23,6.2,3.6,M_STONE,10,yaw=yaw)
    ground("B09_JP_VC_WingInner_"+side,cube,vcx-900,vcy+dy*0.70,
           15,5.0,3.2,M_CONCRETE,10,yaw=yaw)
    spawn("B09_JP_VC_WingRoof_"+side,cube,
          vcx+250,vcy+dy,
          terrain_z(vcx+250,vcy+dy)+395,
          23.6,6.8,0.42,M_RED,yaw=yaw)

# Better front entrance centered toward approach.
ground("B09_JP_VC_Portico",cube,vcx-3550,vcy,11.0,16.0,0.55,M_CONCRETE,95)
for side,dy in [("L",-620),("R",620)]:
    ground("B09_JP_VC_Column_"+side,cyl,vcx-3650,vcy+dy,0.55,0.55,5.8,M_STONE)

# Entry lintel / fascia.
spawn("B09_JP_VC_EntranceLintel",cube,vcx-3650,vcy,
      terrain_z(vcx-3650,vcy)+620,
      1.0,14.0,1.1,M_STONE)

# Forecourt and approach cleaned up.
ground("B09_JP_VC_Forecourt",cyl,vcx-4550,vcy,18.5,18.5,0.10,M_ASPHALT,14)
ground("B09_JP_VC_Approach",cube,vcx-7000,vcy,34,8.0,0.10,M_ASPHALT,12)

# Curbs around approach.
for side,dy in [("L",-470),("R",470)]:
    ground("B09_JP_VC_ApproachCurb_"+side,cube,vcx-7000,vcy+dy,
           34,0.20,0.18,M_CONCRETE,13)

# ============================================================
# 2) MAIN GATE — CORRECTED AUTOMATIC PROPORTIONS
# ============================================================
gx,gy=2016.0,2016.0
gz=terrain_z(gx,gy)

# Approach road aligned through center of opening.
ground("B09_JP_GATE_RoadIn",cube,gx-4200,gy,48,8.5,0.10,M_ASPHALT,12)
ground("B09_JP_GATE_RoadOut",cube,gx+4200,gy,48,8.5,0.10,M_ASPHALT,12)

# Towers spaced wider and made slimmer/taller.
sep=1250.0
tower_h=17.0
for side,dy in [("L",-sep),("R",sep)]:
    ground("B09_JP_GATE_Tower_"+side,cube,gx,gy+dy,
           2.6,2.6,tower_h,M_GATE,0)

    # slightly wider foot
    ground("B09_JP_GATE_Base_"+side,cube,gx,gy+dy,
           3.5,3.5,1.2,M_STONE,0)

    # red top cap
    spawn("B09_JP_GATE_Cap_"+side,cube,gx,gy+dy,
          gz+1790,3.0,3.0,0.7,M_RED)

# Main beam: thinner and higher, seated onto towers.
beam_z=gz+1660
spawn("B09_JP_GATE_MainBeam",cube,gx,gy,beam_z,
      2.3,29.0,1.35,M_GATE)

# Layered top to suggest the familiar Jurassic Park gate crest.
spawn("B09_JP_GATE_UpperBeam",cube,gx-40,gy,gz+1870,
      2.0,24.0,0.55,M_RED)

spawn("B09_JP_GATE_CrestCenter",cube,gx-80,gy,gz+2055,
      1.7,10.5,0.46,M_GATE)

spawn("B09_JP_GATE_CrestL",cube,gx-110,gy-860,gz+2000,
      1.7,8.5,0.42,M_GATE,yaw=-12)

spawn("B09_JP_GATE_CrestR",cube,gx-110,gy+860,gz+2000,
      1.7,8.5,0.42,M_GATE,yaw=12)

# Side vertical fins to give the towers more character.
for side,dy in [("L",-sep),("R",sep)]:
    for j,off in enumerate((-160,160)):
        spawn("B09_JP_GATE_Fin_%s_%d"%(side,j),cube,
              gx-170,gy+dy+off,gz+1040,
              0.38,0.38,10.0,M_RED)

# Road curbs at gate.
for side,dy in [("L",-520),("R",520)]:
    ground("B09_JP_GATE_Curb_"+side,cube,gx,gy+dy,
           95,0.20,0.18,M_CONCRETE,13)

# ============================================================
# 3) CLEAN UP VISUAL CLUTTER IMMEDIATELY AROUND VC + GATE
# ============================================================
# Hide obvious 0.7 green gameplay overlay near Visitor Center.
for a in actor_sub.get_all_level_actors():
    n=a.get_actor_label()
    if n == "B07_JP_Ground_VisitorCenter":
        try:
            a.set_is_temporarily_hidden_in_editor(True)
        except Exception:
            pass

# Hide B06 duplicate visitor center/gate pieces if still visible.
for a in actor_sub.get_all_level_actors():
    n=a.get_actor_label()
    if n.startswith("B06_JP_VisitorCenter_") or n.startswith("B06_JP_Gate_"):
        try:
            a.set_is_temporarily_hidden_in_editor(True)
        except Exception:
            pass

# ============================================================
# 4) SAVE
# ============================================================
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    unreal.EditorLevelLibrary.save_current_level()

created=len(by_prefix("B09_JP_"))
unreal.log("JP BUILD 0.9 COMPLETE: automated VC+gate correction; created=%d" % created)
