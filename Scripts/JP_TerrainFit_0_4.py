import unreal

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.EditorLevelLibrary.get_editor_world()

def get_actor_by_label(label):
    for a in actor_sub.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None

def all_by_prefix(prefix):
    return [a for a in actor_sub.get_all_level_actors() if a.get_actor_label().startswith(prefix)]

def landscape_height(x, y, top_z=100000.0, bottom_z=-100000.0):
    hit = unreal.SystemLibrary.line_trace_single(
        world,
        unreal.Vector(x, y, top_z),
        unreal.Vector(x, y, bottom_z),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
        False,
        [],
        unreal.DrawDebugTrace.NONE,
        True
    )
    if hit and hit[0]:
        return hit[4].z
    return None

def sample_height(x, y, radius=900.0):
    samples = []
    offsets = [
        (0,0),(radius,0),(-radius,0),(0,radius),(0,-radius),
        (radius*0.7,radius*0.7),(-radius*0.7,radius*0.7),
        (radius*0.7,-radius*0.7),(-radius*0.7,-radius*0.7)
    ]
    for dx,dy in offsets:
        h = landscape_height(x+dx, y+dy)
        if h is not None:
            samples.append(h)
    if not samples:
        return None
    samples.sort()
    return samples[len(samples)//2]

def move_actor_to_ground(actor, clearance=20.0, sample_radius=500.0):
    loc = actor.get_actor_location()
    h = sample_height(loc.x, loc.y, sample_radius)
    if h is None:
        unreal.log_warning("No terrain hit for " + actor.get_actor_label())
        return
    actor.set_actor_location(unreal.Vector(loc.x, loc.y, h + clearance), False, False)

road_actors = [a for a in actor_sub.get_all_level_actors()
               if a.get_actor_label().startswith("GB_JP_ARRIVAL_")
               or a.get_actor_label().startswith("GB_JP_TOUR_")]

for a in road_actors:
    move_actor_to_ground(a, 18.0, 300.0)

for label, clearance in {
    "GB_JP_Helipad": 40.0,
    "GB_JP_VisitorCenter_Main": 120.0,
    "GB_JP_VisitorCenter_Rotunda": 120.0,
    "GB_JP_RaptorPen": 80.0,
    "GB_JP_TourGate_L": 40.0,
    "GB_JP_TourGate_R": 40.0,
    "GB_JP_Maintenance": 80.0,
    "GB_JP_PlayerStart": 120.0,
}.items():
    a = get_actor_by_label(label)
    if a:
        move_actor_to_ground(a, clearance, 1200.0 if "VisitorCenter" in label else 700.0)

left = get_actor_by_label("GB_JP_TourGate_L")
right = get_actor_by_label("GB_JP_TourGate_R")
top = get_actor_by_label("GB_JP_TourGate_Top")
if top and left and right:
    z = max(left.get_actor_location().z, right.get_actor_location().z) + 1600.0
    p = top.get_actor_location()
    top.set_actor_location(unreal.Vector(p.x, p.y, z), False, False)

for a in all_by_prefix("GB_JP_ZONE_"):
    move_actor_to_ground(a, 12.0, 1400.0)

asset_lib = unreal.EditorAssetLibrary
cyl = asset_lib.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
if cyl:
    for a in list(actor_sub.get_all_level_actors()):
        if a.get_actor_label().startswith("FIT_JP_BEACON_"):
            actor_sub.destroy_actor(a)

    for marker in all_by_prefix("AUTO_JP_"):
        name = marker.get_actor_label().replace("AUTO_JP_", "")
        p = marker.get_actor_location()
        h = sample_height(p.x, p.y, 500.0)
        if h is None:
            continue
        beacon = actor_sub.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(p.x, p.y, h + 120.0),
            unreal.Rotator()
        )
        beacon.set_actor_label("FIT_JP_BEACON_" + name)
        beacon.static_mesh_component.set_static_mesh(cyl)
        beacon.set_actor_scale3d(unreal.Vector(2.2,2.2,2.5))

for marker in all_by_prefix("AUTO_JP_"):
    try:
        marker.set_is_temporarily_hidden_in_editor(True)
    except Exception:
        pass

unreal.EditorLevelLibrary.save_current_level()
unreal.log("JP Build 0.4 terrain-fit complete.")
