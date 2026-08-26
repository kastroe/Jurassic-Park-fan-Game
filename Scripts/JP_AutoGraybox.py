import unreal
import math

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
asset_lib = unreal.EditorAssetLibrary

cube = asset_lib.load_asset("/Engine/BasicShapes/Cube.Cube")
cyl = asset_lib.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")

if not cube or not cyl:
    raise RuntimeError("Could not load Unreal basic shape assets.")

actors = actor_sub.get_all_level_actors()
markers = {a.get_actor_label().replace("AUTO_JP_", ""): a for a in actors if a.get_actor_label().startswith("AUTO_JP_")}

required = [
    "Waterfall_Helipad","Brachiosaurus_Valley","Visitor_Center","Raptor_Pen",
    "Tour_Gates","Dilophosaurus_Paddock","Triceratops_Field","TRex_Paddock",
    "Maintenance_Compound","Gallimimus_Plain"
]
missing = [n for n in required if n not in markers]
if missing:
    raise RuntimeError("Missing landmark markers: " + ", ".join(missing))

# Remove previous graybox actors.
for a in list(actor_sub.get_all_level_actors()):
    if a.get_actor_label().startswith("GB_JP_"):
        actor_sub.destroy_actor(a)

def spawn_mesh(label, mesh, loc, scale, rot=unreal.Rotator(0,0,0)):
    a = actor_sub.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
    a.set_actor_label(label)
    smc = a.static_mesh_component
    smc.set_static_mesh(mesh)
    a.set_actor_scale3d(scale)
    return a

def marker_loc(name):
    return markers[name].get_actor_location()

# The marker script deliberately put markers high above the island.
# This graybox is also suspended slightly below them so the whole layout
# can be inspected clearly before we terrain-snap/detail it in the next build.
Z = 41000.0

def xy(name):
    p = marker_loc(name)
    return unreal.Vector(p.x, p.y, Z)

def road_between(name_a, name_b, width=700.0, segment_len=1800.0, prefix="ROAD"):
    a = xy(name_a); b = xy(name_b)
    dx, dy = b.x-a.x, b.y-a.y
    dist = math.sqrt(dx*dx + dy*dy)
    n = max(1, int(math.ceil(dist/segment_len)))
    yaw = math.degrees(math.atan2(dy, dx))
    for i in range(n):
        t0=i/n; t1=(i+1)/n; tm=(t0+t1)/2
        x=a.x+dx*tm; y=a.y+dy*tm
        seg=dist/n
        # Engine cube is 100cm each side
        spawn_mesh(f"GB_JP_{prefix}_{name_a}_{name_b}_{i:02d}", cube,
                   unreal.Vector(x,y,Z),
                   unreal.Vector(seg/100.0, width/100.0, 0.12),
                   unreal.Rotator(0,yaw,0))

# Arrival road
road_between("Waterfall_Helipad","Brachiosaurus_Valley", 850, 1600, "ARRIVAL")
road_between("Brachiosaurus_Valley","Visitor_Center", 850, 1600, "ARRIVAL")

# Tour route
tour = ["Visitor_Center","Tour_Gates","Dilophosaurus_Paddock","Triceratops_Field","TRex_Paddock"]
for a,b in zip(tour,tour[1:]):
    road_between(a,b, 700, 1500, "TOUR")

# Visitor Center massing
v = xy("Visitor_Center")
spawn_mesh("GB_JP_VisitorCenter_Main", cube, unreal.Vector(v.x,v.y,Z+900),
           unreal.Vector(34,24,9))
spawn_mesh("GB_JP_VisitorCenter_Rotunda", cyl, unreal.Vector(v.x-2600,v.y,Z+1300),
           unreal.Vector(16,16,13))

# Raptor pen
r = xy("Raptor_Pen")
spawn_mesh("GB_JP_RaptorPen", cyl, unreal.Vector(r.x,r.y,Z+700),
           unreal.Vector(11,11,7))

# Helipad
h = xy("Waterfall_Helipad")
spawn_mesh("GB_JP_Helipad", cyl, unreal.Vector(h.x,h.y,Z+90),
           unreal.Vector(9,9,0.35))

# Tour gates - two pillars + overhead beam
g = xy("Tour_Gates")
spawn_mesh("GB_JP_TourGate_L", cube, unreal.Vector(g.x,g.y-650,Z+850), unreal.Vector(2.2,2.2,8.5))
spawn_mesh("GB_JP_TourGate_R", cube, unreal.Vector(g.x,g.y+650,Z+850), unreal.Vector(2.2,2.2,8.5))
spawn_mesh("GB_JP_TourGate_Top", cube, unreal.Vector(g.x,g.y,Z+1650), unreal.Vector(2.2,15,1.6))

# Paddock/field pads to make areas obvious
for name, sx, sy in [
    ("Brachiosaurus_Valley", 34, 28),
    ("Dilophosaurus_Paddock", 24, 20),
    ("Triceratops_Field", 26, 21),
    ("TRex_Paddock", 32, 24),
    ("Gallimimus_Plain", 35, 26),
]:
    p = xy(name)
    spawn_mesh("GB_JP_ZONE_"+name, cube, unreal.Vector(p.x,p.y,Z-150),
               unreal.Vector(sx,sy,0.08))

# Maintenance compound
m = xy("Maintenance_Compound")
spawn_mesh("GB_JP_Maintenance", cube, unreal.Vector(m.x,m.y,Z+500),
           unreal.Vector(18,13,5))

# Add a PlayerStart near Visitor Center for later quick testing.
for a in list(actor_sub.get_all_level_actors()):
    if a.get_actor_label() == "GB_JP_PlayerStart":
        actor_sub.destroy_actor(a)
ps = actor_sub.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(v.x+2500,v.y,Z+350), unreal.Rotator())
ps.set_actor_label("GB_JP_PlayerStart")

unreal.EditorLevelLibrary.save_current_level()
unreal.log("JP Build 0.3: Auto-graybox created successfully.")
