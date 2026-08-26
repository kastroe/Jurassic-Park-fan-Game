import unreal

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.EditorLevelLibrary.get_editor_world()

actors = actor_sub.get_all_level_actors()

def by_prefix(prefix):
    return [a for a in actor_sub.get_all_level_actors()
            if a.get_actor_label().startswith(prefix)]

def by_label(label):
    for a in actor_sub.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None

# Ignore all of our floating helper/blockout actors when tracing down.
ignore_for_ground = []
for a in actors:
    label = a.get_actor_label()
    if (label.startswith("GB_JP_") or label.startswith("AUTO_JP_")
            or label.startswith("FIT_JP_")):
        ignore_for_ground.append(a)

def ground_z(x, y):
    hit = unreal.SystemLibrary.line_trace_single(
        world,
        unreal.Vector(x, y, 150000.0),
        unreal.Vector(x, y, -150000.0),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
        False,
        ignore_for_ground,
        unreal.DrawDebugTrace.NONE,
        True
    )
    if hit and hit[0]:
        return hit[4].z
    return None

def actor_half_height(actor):
    # Uses the actor's current rendered bounds, so large buildings sit ON the ground
    # rather than having their centre placed at ground level.
    origin, extent = actor.get_actor_bounds(False)
    return max(5.0, extent.z)

def place_on_ground(actor, extra=10.0):
    p = actor.get_actor_location()
    z = ground_z(p.x, p.y)
    if z is None:
        unreal.log_warning("No landscape hit beneath " + actor.get_actor_label())
        return False
    half = actor_half_height(actor)
    actor.set_actor_location(
        unreal.Vector(p.x, p.y, z + half + extra),
        False, False
    )
    return True

# Roads first.
roads = [a for a in actor_sub.get_all_level_actors()
         if a.get_actor_label().startswith("GB_JP_ARRIVAL_")
         or a.get_actor_label().startswith("GB_JP_TOUR_")]

for a in roads:
    place_on_ground(a, 4.0)

# Ground zones and main structures.
for prefix in ["GB_JP_ZONE_"]:
    for a in by_prefix(prefix):
        place_on_ground(a, 4.0)

for label in [
    "GB_JP_Helipad",
    "GB_JP_VisitorCenter_Main",
    "GB_JP_VisitorCenter_Rotunda",
    "GB_JP_RaptorPen",
    "GB_JP_TourGate_L",
    "GB_JP_TourGate_R",
    "GB_JP_Maintenance",
    "GB_JP_PlayerStart",
]:
    a = by_label(label)
    if a:
        place_on_ground(a, 10.0)

# Gate top is positioned from the grounded pillars rather than from terrain.
left = by_label("GB_JP_TourGate_L")
right = by_label("GB_JP_TourGate_R")
top = by_label("GB_JP_TourGate_Top")
if left and right and top:
    lp = left.get_actor_location()
    rp = right.get_actor_location()
    # place beam above the two pillars using their bounds
    _, le = left.get_actor_bounds(False)
    _, re = right.get_actor_bounds(False)
    _, te = top.get_actor_bounds(False)
    pillar_top = max(lp.z + le.z, rp.z + re.z)
    tp = top.get_actor_location()
    top.set_actor_location(
        unreal.Vector(tp.x, tp.y, pillar_top + te.z + 10.0),
        False, False
    )

# Rebuild ground beacons, also ignoring helper geometry during trace.
for a in list(by_prefix("FIT_JP_BEACON_")):
    actor_sub.destroy_actor(a)

cyl = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
if cyl:
    for marker in by_prefix("AUTO_JP_"):
        p = marker.get_actor_location()
        z = ground_z(p.x, p.y)
        if z is None:
            continue
        beacon = actor_sub.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(p.x, p.y, z + 125.0),
            unreal.Rotator()
        )
        beacon.set_actor_label(
            "FIT_JP_BEACON_" + marker.get_actor_label().replace("AUTO_JP_", "")
        )
        beacon.static_mesh_component.set_static_mesh(cyl)
        beacon.set_actor_scale3d(unreal.Vector(2.0, 2.0, 2.5))

# Hide the high marker actors in the editor after the fit.
for marker in by_prefix("AUTO_JP_"):
    marker.set_is_temporarily_hidden_in_editor(True)

unreal.EditorLevelLibrary.save_current_level()
unreal.log("JP Build 0.4.1: terrain-fit corrected. Helper geometry was ignored by ground traces.")
