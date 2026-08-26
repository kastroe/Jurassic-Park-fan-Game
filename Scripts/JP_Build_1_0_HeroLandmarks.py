import unreal, os, struct, zlib, math

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assetlib = unreal.EditorAssetLibrary
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
matlib = unreal.MaterialEditingLibrary

PROJECT = unreal.Paths.project_dir()
HEIGHTMAP = os.path.join(PROJECT, "Content", "JPBlockout", "JP_Island_Heightmap_2017_v05.png")
if not os.path.exists(HEIGHTMAP):
    raise RuntimeError("Missing heightmap: " + HEIGHTMAP)

def read_png16_gray(path):
    with open(path,"rb") as f: data=f.read()
    pos=8; idat=bytearray()
    while pos < len(data):
        ln=struct.unpack(">I",data[pos:pos+4])[0]
        typ=data[pos+4:pos+8]
        chunk=data[pos+8:pos+8+ln]
        pos += 12+ln
        if typ==b"IHDR":
            width,height,bd,ct,_,_,interlace=struct.unpack(">IIBBBBB",chunk)
        elif typ==b"IDAT":
            idat.extend(chunk)
        elif typ==b"IEND":
            break
    raw=zlib.decompress(bytes(idat))
    stride=width*2; prev=bytearray(stride); rows=[]; p=0
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
MINX=MINY=-100800.0
PER=100.0

def terrain_z(x,y):
    fx=max(0,min(W-1.001,(x-MINX)/PER)); fy=max(0,min(H-1.001,(y-MINY)/PER))
    x0=int(fx); y0=int(fy); x1=min(W-1,x0+1); y1=min(H-1,y0+1)
    tx=fx-x0; ty=fy-y0
    v=(HM[y0][x0]*(1-tx)*(1-ty)+HM[y0][x1]*tx*(1-ty)+HM[y1][x0]*(1-tx)*ty+HM[y1][x1]*tx*ty)
    return (float(v)-32768.0)*100.0/128.0

cube=assetlib.load_asset("/Engine/BasicShapes/Cube.Cube")
cyl=assetlib.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
cone=assetlib.load_asset("/Engine/BasicShapes/Cone.Cone")
sphere=assetlib.load_asset("/Engine/BasicShapes/Sphere.Sphere")

MAT_DIR="/Game/JPGenerated/Materials"
if not assetlib.does_directory_exist(MAT_DIR): assetlib.make_directory(MAT_DIR)

def make_mat(name,rgb,rough=.8,metal=0):
    p=MAT_DIR+"/"+name
    if assetlib.does_asset_exist(p): return assetlib.load_asset(p)
    m=asset_tools.create_asset(name,MAT_DIR,unreal.Material,unreal.MaterialFactoryNew())
    c=matlib.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-300,-50)
    c.constant=unreal.LinearColor(rgb[0],rgb[1],rgb[2],1)
    matlib.connect_material_property(c,"",unreal.MaterialProperty.MP_BASE_COLOR)
    r=matlib.create_material_expression(m,unreal.MaterialExpressionConstant,-300,50); r.r=rough
    matlib.connect_material_property(r,"",unreal.MaterialProperty.MP_ROUGHNESS)
    mt=matlib.create_material_expression(m,unreal.MaterialExpressionConstant,-300,140); mt.r=metal
    matlib.connect_material_property(mt,"",unreal.MaterialProperty.MP_METALLIC)
    matlib.recompile_material(m); assetlib.save_asset(p,only_if_is_dirty=False)
    return m

M_CONCRETE=make_mat("M_JP_Concrete",(0.36,0.34,0.29),.82)
M_STONE=make_mat("M_JP_Stone",(0.17,0.16,0.13),.9)
M_ASPHALT=make_mat("M_JP_Asphalt",(0.035,0.04,0.045),.88)
M_GATE=make_mat("M_JP_GateDark",(0.055,0.035,0.02),.78,.1)
M_ROOF=make_mat("M_JP_ThatchApprox",(0.29,0.20,0.11),.96)
M_WOOD=make_mat("M_JP_DarkWood",(0.105,0.048,0.018),.92)
M_SIGN=make_mat("M_JP_SignRed",(0.35,0.018,0.012),.72)
M_GOLD=make_mat("M_JP_SignGold",(0.72,0.43,0.04),.65,.15)
M_FLAME=make_mat("M_JP_FlameBlockout",(0.95,0.19,0.02),.30)
M_GLASS=make_mat("M_JP_GlassDark",(0.025,0.055,0.05),.25,.05)

def by_prefix(p): return [a for a in actor_sub.get_all_level_actors() if a.get_actor_label().startswith(p)]
def set_mat(a,m):
    try:a.static_mesh_component.set_material(0,m)
    except:pass
def spawn(label,mesh,x,y,z,sx,sy,sz,mat=None,yaw=0,pitch=0):
    a=actor_sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(x,y,z),unreal.Rotator(pitch,yaw,0))
    a.set_actor_label(label); a.static_mesh_component.set_static_mesh(mesh); a.set_actor_scale3d(unreal.Vector(sx,sy,sz))
    if mat:set_mat(a,mat)
    return a
def ground(label,mesh,x,y,sx,sy,sz,mat=None,extra=0,yaw=0,pitch=0):
    return spawn(label,mesh,x,y,terrain_z(x,y)+sz*50+extra,sx,sy,sz,mat,yaw,pitch)

for a in list(by_prefix("B10_JP_")): actor_sub.destroy_actor(a)
for a in actor_sub.get_all_level_actors():
    n=a.get_actor_label()
    if n.startswith(("B09_JP_VC_","B09_JP_GATE_","B08_JP_VC_","B08_JP_GATE_","B06_JP_VisitorCenter_","B06_JP_Gate_")):
        try:a.set_is_temporarily_hidden_in_editor(True)
        except:pass

# Visitor Center
vcx,vcy=-10080.0,-3024.0; vcz=terrain_z(vcx,vcy); cx=vcx-800
ground("B10_JP_VC_Terrace",cube,vcx-700,vcy,54,42,.18,M_STONE,10)
ground("B10_JP_VC_CentralBody",cyl,cx,vcy,20,20,5.2,M_CONCRETE,10)
spawn("B10_JP_VC_CentralGlassBand",cyl,cx,vcy,vcz+470,20.5,20.5,.55,M_GLASS)
spawn("B10_JP_VC_CentralRoof",cone,cx,vcy,vcz+1040,25,25,4.6,M_ROOF)
spawn("B10_JP_VC_CupolaBody",cyl,cx,vcy,vcz+1275,6.8,6.8,2.0,M_CONCRETE)
spawn("B10_JP_VC_CupolaRoof",cone,cx,vcy,vcz+1515,8.2,8.2,3.0,M_ROOF)

for side,dy in [("L",-4300),("R",4300)]:
    sx=vcx+100; sy=vcy+dy; sz=terrain_z(sx,sy)
    ground("B10_JP_VC_SideBody_"+side,cyl,sx,sy,14.5,14.5,4.2,M_CONCRETE,10)
    spawn("B10_JP_VC_SideGlass_"+side,cyl,sx,sy,sz+380,14.8,14.8,.45,M_GLASS)
    spawn("B10_JP_VC_SideRoof_"+side,cone,sx,sy,sz+825,18.5,18.5,4.1,M_ROOF)
    spawn("B10_JP_VC_SideCupola_"+side,cone,sx,sy,sz+1080,5.8,5.8,3.0,M_ROOF)

for side,dy in [("L",-2350),("R",2350)]:
    ground("B10_JP_VC_Connector_"+side,cube,vcx-200,vcy+dy,24,9,3.8,M_CONCRETE,10)

ex=vcx-3150
ground("B10_JP_VC_EntranceTower",cube,ex,vcy,8,12,6.2,M_STONE,10)
ground("B10_JP_VC_Door",cube,ex-420,vcy,.55,5,4.5,M_WOOD,15)
for i,dy in enumerate([-1450,-950,-450,450,950,1450]):
    ground("B10_JP_VC_FrontColumn_%02d"%i,cyl,vcx-2450,vcy+dy,.38,.38,5,M_CONCRETE,10)
for i in range(9):
    x=vcx-4200-i*230; width=17+i*1.1
    ground("B10_JP_VC_Stair_%02d"%i,cube,x,vcy,width,.95,.20,M_CONCRETE,10+i*10)
ground("B10_JP_VC_Forecourt",cube,vcx-6600,vcy,38,16,.10,M_ASPHALT,12)

# Gate
gx,gy=2016.0,2016.0; gz=terrain_z(gx,gy); sep=1550.0
for side,dy in [("L",-sep),("R",sep)]:
    for j,(zoff,sx,sy,sz) in enumerate([(0,3.8,3.8,5),(460,3.45,3.45,4.2),(860,3.1,3.1,3.7),(1210,2.75,2.75,3.2),(1510,2.45,2.45,2.8)]):
        spawn("B10_JP_GATE_Tower_%s_%d"%(side,j),cube,gx,gy+dy,gz+zoff+sz*50,sx,sy,sz,M_STONE)
    spawn("B10_JP_GATE_TowerCap_"+side,cone,gx,gy+dy,gz+2050,3,3,7.5,M_STONE)

door_z=gz+13.8*50
spawn("B10_JP_GATE_Door_L",cube,gx-60,gy-690,door_z,.50,13.5,13.8,M_WOOD)
spawn("B10_JP_GATE_Door_R",cube,gx-60,gy+690,door_z,.50,13.5,13.8,M_WOOD)
spawn("B10_JP_GATE_CenterPost",cube,gx-110,gy,gz+700,.75,.75,14,M_GATE)
spawn("B10_JP_GATE_Diagonal_L",cube,gx-130,gy-690,gz+760,.30,14.5,.65,M_GATE,yaw=-28)
spawn("B10_JP_GATE_Diagonal_R",cube,gx-130,gy+690,gz+760,.30,14.5,.65,M_GATE,yaw=28)

for i in range(13):
    y=-1500+3000*(i/12)
    z=gz+1930+260*(1-(abs(y)/1500.0)**2)
    spawn("B10_JP_GATE_Arch_%02d"%i,cube,gx-50,gy+y,z,.9,2.8,.85,M_GATE)

spawn("B10_JP_GATE_SignPlate",cube,gx-140,gy,gz+2160,.55,13,3.5,M_SIGN)
for idx,dy in enumerate([-700,-350,0,350,700]):
    spawn("B10_JP_GATE_SignAccent_%d"%idx,cube,gx-180,gy+dy,gz+2170,.28,1.6,3.0,M_GOLD)

for side,dy in [("L",-sep),("R",sep)]:
    inner=1 if side=="L" else -1
    for j,zoff in enumerate([470,1050,1580]):
        y=gy+dy+inner*340
        spawn("B10_JP_GATE_TorchCup_%s_%d"%(side,j),cube,gx-240,y,gz+zoff,.6,.9,.5,M_GATE)
        spawn("B10_JP_GATE_Flame_%s_%d"%(side,j),sphere,gx-270,y,gz+zoff+85,.55,.55,.85,M_FLAME)
    spawn("B10_JP_GATE_TopFlame_"+side,sphere,gx,gy+dy,gz+2470,.9,.9,1.25,M_FLAME)

ground("B10_JP_GATE_RoadApproach",cube,gx-4800,gy,55,9,.10,M_ASPHALT,12)
ground("B10_JP_GATE_RoadExit",cube,gx+4800,gy,55,9,.10,M_ASPHALT,12)

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except:
    unreal.EditorLevelLibrary.save_current_level()

unreal.log("JP BUILD 1.0 COMPLETE: hero landmark rebuild; created=%d" % len(by_prefix("B10_JP_")))
