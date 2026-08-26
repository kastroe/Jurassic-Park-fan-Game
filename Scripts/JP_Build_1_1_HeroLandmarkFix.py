import unreal, os, struct, zlib, math

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assetlib = unreal.EditorAssetLibrary

PROJECT = unreal.Paths.project_dir()
HEIGHTMAP = os.path.join(PROJECT, "Content", "JPBlockout", "JP_Island_Heightmap_2017_v05.png")
if not os.path.exists(HEIGHTMAP):
    raise RuntimeError("Missing heightmap: " + HEIGHTMAP)

# ---------------- Heightmap ----------------
def read_png16_gray(path):
    with open(path,"rb") as f: data=f.read()
    pos=8; idat=bytearray()
    while pos < len(data):
        ln=struct.unpack(">I",data[pos:pos+4])[0]
        typ=data[pos+4:pos+8]; chunk=data[pos+8:pos+8+ln]
        pos += 12+ln
        if typ==b"IHDR":
            width,height,bd,ct,_,_,interlace=struct.unpack(">IIBBBBB",chunk)
        elif typ==b"IDAT": idat.extend(chunk)
        elif typ==b"IEND": break
    raw=zlib.decompress(bytes(idat)); stride=width*2; prev=bytearray(stride); rows=[]; p=0
    def paeth(a,b,c):
        q=a+b-c; pa,pb,pc=abs(q-a),abs(q-b),abs(q-c)
        return a if pa<=pb and pa<=pc else (b if pb<=pc else c)
    for _ in range(height):
        ft=raw[p]; p+=1
        scan=bytearray(raw[p:p+stride]); p+=stride
        recon=bytearray(stride)
        for i in range(stride):
            x=scan[i]; a=recon[i-2] if i>=2 else 0; b=prev[i]; c=prev[i-2] if i>=2 else 0
            if ft==0:v=x
            elif ft==1:v=(x+a)&255
            elif ft==2:v=(x+b)&255
            elif ft==3:v=(x+((a+b)//2))&255
            elif ft==4:v=(x+paeth(a,b,c))&255
            recon[i]=v
        rows.append([(recon[i]<<8)|recon[i+1] for i in range(0,stride,2)])
        prev=recon
    return width,height,rows

W,H,HM=read_png16_gray(HEIGHTMAP)
MINX=MINY=-100800.0; PER=100.0
def terrain_z(x,y):
    fx=max(0,min(W-1.001,(x-MINX)/PER)); fy=max(0,min(H-1.001,(y-MINY)/PER))
    x0=int(fx); y0=int(fy); x1=min(W-1,x0+1); y1=min(H-1,y0+1)
    tx=fx-x0; ty=fy-y0
    v=(HM[y0][x0]*(1-tx)*(1-ty)+HM[y0][x1]*tx*(1-ty)+HM[y1][x0]*(1-tx)*ty+HM[y1][x1]*tx*ty)
    return (float(v)-32768.0)*100.0/128.0

# ---------------- Assets & materials ----------------
cube=assetlib.load_asset("/Engine/BasicShapes/Cube.Cube")
cyl=assetlib.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
cone=assetlib.load_asset("/Engine/BasicShapes/Cone.Cone")

MAT_DIR="/Game/JPGenerated/Materials"
def mat(name):
    p=MAT_DIR+"/"+name
    return assetlib.load_asset(p) if assetlib.does_asset_exist(p) else None

M_CONCRETE=mat("M_JP_Concrete")
M_STONE=mat("M_JP_Stone")
M_ASPHALT=mat("M_JP_Asphalt")
M_GATE=mat("M_JP_GateDark")
M_ROOF=mat("M_JP_ThatchApprox")
M_WOOD=mat("M_JP_DarkWood")
M_GLASS=mat("M_JP_GlassDark")

def by_prefix(p): return [a for a in actor_sub.get_all_level_actors() if a.get_actor_label().startswith(p)]
def set_mat(a,m):
    if not m: return
    try:a.static_mesh_component.set_material(0,m)
    except:pass

def spawn(label,mesh,x,y,z,sx,sy,sz,m=None,yaw=0,pitch=0,roll=0):
    a=actor_sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(x,y,z),unreal.Rotator(pitch,yaw,roll))
    a.set_actor_label(label); a.static_mesh_component.set_static_mesh(mesh); a.set_actor_scale3d(unreal.Vector(sx,sy,sz))
    set_mat(a,m); return a

def ground(label,mesh,x,y,sx,sy,sz,m=None,extra=0,yaw=0):
    return spawn(label,mesh,x,y,terrain_z(x,y)+sz*50+extra,sx,sy,sz,m,yaw)

# Remove previous 1.1; hide 1.0 Visitor Center only.
for a in list(by_prefix("B11_JP_")): actor_sub.destroy_actor(a)
for a in actor_sub.get_all_level_actors():
    n=a.get_actor_label()
    if n.startswith("B10_JP_VC_"):
        try:a.set_is_temporarily_hidden_in_editor(True)
        except:pass

# ============================================================
# VISITOR CENTER 1.1
# Corrected after inspection of Build 1.0:
# - front-facing rather than stacked from above
# - wider, lower three-pavilion composition
# - entrance/stairs integrated into central facade
# ============================================================
vcx,vcy=-10080.0,-3024.0
vcz=terrain_z(vcx,vcy)

# broad terrace
ground("B11_JP_VC_Terrace",cube,vcx-900,vcy,66,44,0.18,M_STONE,10)

# central hall shifted rearward so facade/entrance reads from road side
cx=vcx+450
ground("B11_JP_VC_CentralBody",cyl,cx,vcy,21.5,21.5,4.6,M_CONCRETE,10)
spawn("B11_JP_VC_CentralGlassBand",cyl,cx,vcy,vcz+390,21.7,21.7,0.48,M_GLASS)
spawn("B11_JP_VC_CentralRoof",cone,cx,vcy,vcz+850,26.5,26.5,3.4,M_ROOF)
spawn("B11_JP_VC_CupolaBody",cyl,cx,vcy,vcz+1090,6.8,6.8,1.5,M_CONCRETE)
spawn("B11_JP_VC_CupolaRoof",cone,cx,vcy,vcz+1275,7.5,7.5,2.0,M_ROOF)

# side pavilions closer to central hall, matching reference width
for side,dy in [("L",-3600),("R",3600)]:
    sx=vcx+900; sy=vcy+dy; sz=terrain_z(sx,sy)
    ground("B11_JP_VC_SideBody_"+side,cyl,sx,sy,14.5,14.5,3.9,M_CONCRETE,10)
    spawn("B11_JP_VC_SideGlass_"+side,cyl,sx,sy,sz+330,14.7,14.7,0.42,M_GLASS)
    spawn("B11_JP_VC_SideRoof_"+side,cone,sx,sy,sz+730,18.4,18.4,3.1,M_ROOF)
    spawn("B11_JP_VC_SideCupola_"+side,cone,sx,sy,sz+930,5.4,5.4,1.9,M_ROOF)

# low curved-feel connector masses
for side,dy in [("L",-2050),("R",2050)]:
    ground("B11_JP_VC_Connector_"+side,cube,vcx+350,vcy+dy,26,9,3.1,M_CONCRETE,10)

# central projecting entrance at front
front_x=vcx-2900
ground("B11_JP_VC_Entrance",cube,front_x,vcy,8,11,5.0,M_STONE,10)
ground("B11_JP_VC_Door",cube,front_x-430,vcy,0.5,4.0,4.1,M_WOOD,18)

# entrance surround
for side,dy in [("L",-430),("R",430)]:
    ground("B11_JP_VC_DoorPier_"+side,cube,front_x-500,vcy+dy,0.8,0.8,5.0,M_STONE,10)
spawn("B11_JP_VC_DoorLintel",cube,front_x-500,vcy,terrain_z(front_x-500,vcy)+540,0.8,10.0,0.65,M_STONE)

# front colonnade across central pavilion
for i,dy in enumerate([-1450,-1000,-550,550,1000,1450]):
    ground("B11_JP_VC_Column_%02d"%i,cyl,vcx-1850,vcy+dy,0.38,0.38,4.4,M_CONCRETE,10)

# broad central stair flight, centered exactly on door
for i in range(10):
    x=vcx-3500-i*210
    ground("B11_JP_VC_Stair_%02d"%i,cube,x,vcy,15.5+i*1.25,1.0,0.18,M_CONCRETE,8+i*11)

# planter/wing walls
ground("B11_JP_VC_Planter_L",cube,vcx-4200,vcy-1500,19,2.1,1.25,M_CONCRETE,10,yaw=-14)
ground("B11_JP_VC_Planter_R",cube,vcx-4200,vcy+1500,19,2.1,1.25,M_CONCRETE,10,yaw=14)

# road-facing forecourt
ground("B11_JP_VC_Forecourt",cube,vcx-6200,vcy,38,15,0.10,M_ASPHALT,12)

# Save
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except:
    unreal.EditorLevelLibrary.save_current_level()

unreal.log("JP BUILD 1.1 COMPLETE: Visitor Center correction; created=%d" % len(by_prefix("B11_JP_")))
