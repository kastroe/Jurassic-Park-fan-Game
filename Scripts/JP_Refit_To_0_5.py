import unreal, os, struct, zlib

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
project_dir = unreal.Paths.project_dir()
png_path = os.path.join(project_dir, "Content", "JPBlockout", "JP_Island_Heightmap_2017_v05.png")

if not os.path.exists(png_path):
    raise RuntimeError("Missing Build 0.5 heightmap: " + png_path)

def read_png16_gray(path):
    with open(path,"rb") as f:
        data=f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("Not a PNG")
    pos=8; idat=bytearray()
    width=height=bit_depth=color_type=None
    while pos < len(data):
        ln=struct.unpack(">I",data[pos:pos+4])[0]
        typ=data[pos+4:pos+8]
        chunk=data[pos+8:pos+8+ln]
        pos += 12+ln
        if typ==b"IHDR":
            width,height,bit_depth,color_type,_,_,interlace=struct.unpack(">IIBBBBB",chunk)
            if bit_depth!=16 or color_type!=0 or interlace!=0:
                raise RuntimeError("Expected non-interlaced 16-bit grayscale PNG")
        elif typ==b"IDAT":
            idat.extend(chunk)
        elif typ==b"IEND":
            break
    raw=zlib.decompress(bytes(idat))
    stride=width*2; prev=bytearray(stride); rows=[]; p=0
    def paeth(a,b,c):
        q=a+b-c; pa=abs(q-a); pb=abs(q-b); pc=abs(q-c)
        return a if pa<=pb and pa<=pc else (b if pb<=pc else c)
    for _ in range(height):
        ft=raw[p]; p+=1
        scan=bytearray(raw[p:p+stride]); p+=stride
        recon=bytearray(stride)
        for i in range(stride):
            x=scan[i]; a=recon[i-2] if i>=2 else 0; b=prev[i]; c=prev[i-2] if i>=2 else 0
            if ft==0: v=x
            elif ft==1: v=(x+a)&255
            elif ft==2: v=(x+b)&255
            elif ft==3: v=(x+((a+b)//2))&255
            elif ft==4: v=(x+paeth(a,b,c))&255
            else: raise RuntimeError("Unsupported PNG filter")
            recon[i]=v
        row=[(recon[i]<<8)|recon[i+1] for i in range(0,stride,2)]
        rows.append(row); prev=recon
    return width,height,rows

W,H,HM=read_png16_gray(png_path)
MINX=MINY=-100800.0
PER=100.0

def h_at(x,y):
    fx=max(0,min(W-1.001,(x-MINX)/PER))
    fy=max(0,min(H-1.001,(y-MINY)/PER))
    x0=int(fx); y0=int(fy); x1=min(W-1,x0+1); y1=min(H-1,y0+1)
    tx=fx-x0; ty=fy-y0
    v=(HM[y0][x0]*(1-tx)*(1-ty)+HM[y0][x1]*tx*(1-ty)+HM[y1][x0]*(1-tx)*ty+HM[y1][x1]*tx*ty)
    return (float(v)-32768.0)*100.0/128.0

def prefix(p):
    return [a for a in actor_sub.get_all_level_actors() if a.get_actor_label().startswith(p)]

def label(name):
    for a in actor_sub.get_all_level_actors():
        if a.get_actor_label()==name: return a
    return None

def halfheight(a):
    try:
        _,e=a.get_actor_bounds(False); return max(5,float(e.z))
    except: return 5.0

def ground(a,extra=5):
    p=a.get_actor_location()
    a.set_actor_location(unreal.Vector(p.x,p.y,h_at(p.x,p.y)+halfheight(a)+extra),False,False)

moved=0
for a in actor_sub.get_all_level_actors():
    n=a.get_actor_label()
    if n.startswith("GB_JP_ARRIVAL_") or n.startswith("GB_JP_TOUR_") or n.startswith("GB_JP_ZONE_"):
        ground(a,3); moved+=1

for n in ["GB_JP_Helipad","GB_JP_VisitorCenter_Main","GB_JP_VisitorCenter_Rotunda",
          "GB_JP_RaptorPen","GB_JP_TourGate_L","GB_JP_TourGate_R","GB_JP_Maintenance",
          "GB_JP_PlayerStart"]:
    a=label(n)
    if a: ground(a,8); moved+=1

L=label("GB_JP_TourGate_L"); R=label("GB_JP_TourGate_R"); T=label("GB_JP_TourGate_Top")
if L and R and T:
    lp=L.get_actor_location(); rp=R.get_actor_location()
    _,le=L.get_actor_bounds(False); _,re=R.get_actor_bounds(False); _,te=T.get_actor_bounds(False)
    topz=max(lp.z+le.z,rp.z+re.z)
    p=T.get_actor_location()
    T.set_actor_location(unreal.Vector(p.x,p.y,topz+te.z+10),False,False)
    moved+=1

for a in list(prefix("FIT_JP_BEACON_")):
    actor_sub.destroy_actor(a)

cyl=unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
if cyl:
    for m in prefix("AUTO_JP_"):
        p=m.get_actor_location()
        b=actor_sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(p.x,p.y,h_at(p.x,p.y)+125),unreal.Rotator())
        b.set_actor_label("FIT_JP_BEACON_"+m.get_actor_label().replace("AUTO_JP_",""))
        b.static_mesh_component.set_static_mesh(cyl)
        b.set_actor_scale3d(unreal.Vector(2,2,2.5))
        try: m.set_is_temporarily_hidden_in_editor(True)
        except: pass

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except:
    unreal.EditorLevelLibrary.save_current_level()

unreal.log("JP BUILD 0.5 REFIT COMPLETE: moved=%d" % moved)
