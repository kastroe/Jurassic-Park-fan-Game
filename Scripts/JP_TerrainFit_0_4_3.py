import unreal

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.EditorLevelLibrary.get_editor_world()

def by_prefix(prefix):
    return [a for a in actor_sub.get_all_level_actors()
            if a.get_actor_label().startswith(prefix)]

def by_label(label):
    for a in actor_sub.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None

# Ignore all of our temporary helper actors so traces reach the landscape.
ignore_for_ground = []
for a in actor_sub.get_all_level_actors():
    label = a.get_actor_label()
    if label.startswith("GB_JP_") or label.startswith("AUTO_JP_") or label.startswith("FIT_JP_"):
        ignore_for_ground.append(a)

def ground_z(x, y):
    hit = unreal.SystemLibrary.line_trace_single(
        world,
        unreal.Vector(x, y, 150000.0),
        unreal.Vector(x, y, -150000.0),
        unreal.TraceTypeQuery.ECC_VISIBILITY,
        False,
        ignore_for_ground,
        unreal.DrawDebugTrace.NONE,
        True
    )

    # UE's Python trace API returns None when nothing is hit.
    # On this UE 5.8 build the HitResult's bitfield 'blocking_hit' is not
    # exposed to Python, so do NOT query it.
    if hit is None:
        return None

    # Try normal Python struct properties first.
    try:
        return float(hit.impact_point.z)
    except Exception:
        pass

    try:
        return float(hit.location.z)
    except Exception:
        pass

    # Fallback for differences in generated Python bindings.
    for prop in ("impact_point", "location"):
        try:
            v = hit.get_editor_property(prop)
            return float(v.z)
        except Exception:
            pass

    unreal.log_error("HitResult existed but no impact/location property could be read.")
    return None

def actor_half_height(actor):
    try:
        origin, extent = actor.get_actor_bounds(False)
        return max(5.0, float(extent.z))
    except Exception:
        return 5.0

def place_on_ground(actor, extra=10.0):
    p = actor.get_actor_location()
    z = ground_z(p.x, p.y)
    if z is None:
        unreal.log_warning("No landscape hit beneath " + actor.get_actor_label())
        return False

    actor.set_actor_location(
        unreal.Vector(p.x, p.y, z + actor_half_height(actor) + extra),
        False,
        False
    )
    return True

roads = [
    a for a in actor_sub.get_all_level_actors()
    if a.get_actor_label().startswith("GB_JP_ARRIVAL_")
    or a.get_actor_label().startswith("GB_JP_TOUR_")
]

moved = 0
missed = 0

for a in roads:
    if place_on_ground(a, 4.0):
        moved += 1
    else:
        missed += 1

for a in by_prefix("GB_JP_ZONE_"):
    if place_on_ground(a, 4.0):
        moved += 1
    else:
        missed += 1

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
        if place_on_ground(a, 10.0):
            moved += 1
        else:
            missed += 1

# Reposition tour-gate overhead beam from the grounded pillars.
left = by_label("GB_JP_TourGate_L")
right = by_label("GB_JP_TourGate_R")
top = by_label("GB_JP_TourGate_Top")

if left and right and top:
    lp = left.get_actor_location()
    rp = right.get_actor_location()
    _, le = left.get_actor_bounds(False)
    _, re = right.get_actor_bounds(False)
    _, te = top.get_actor_bounds(False)

    pillar_top = max(lp.z + le.z, rp.z + re.z)
    tp = top.get_actor_location()
    top.set_actor_location(
        unreal.Vector(tp.x, tp.y, pillar_top + te.z + 10.0),
        False,
        False
    )

# Remove previous beacons and rebuild them at ground level.
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

# Only hide the high markers if we actually moved graybox objects.
if moved > 0:
    for marker in by_prefix("AUTO_JP_"):
        try:
            marker.set_is_temporarily_hidden_in_editor(True)
        except Exception:
            pass

unreal.EditorLevelLibrary.save_current_level()

unreal.log(
    "JP BUILD 0.4.3 COMPLETE: moved=%d missed=%d" % (moved, missed)
)
