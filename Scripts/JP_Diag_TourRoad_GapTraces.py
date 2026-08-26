import math

import unreal


EXPECTED_MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"


try:
    world = unreal.EditorLevelLibrary.get_editor_world()
    if world.get_outermost().get_name() != EXPECTED_MAP:
        raise RuntimeError(f"Unexpected map {world.get_outermost().get_name()}")

    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    guide = next(a for a in actors if a.get_actor_label() == "TOUR_RoadGuide")
    spline = guide.get_component_by_class(unreal.SplineComponent)
    length = spline.get_spline_length()

    roads = [a for a in actors if a.get_actor_label().startswith("TOUR_FinalRoad_")]
    roads.sort(key=lambda a: a.get_actor_label())

    object_types = [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1]

    def landscape_z(x, y):
        hit = unreal.SystemLibrary.line_trace_single_for_objects(
            world,
            unreal.Vector(x, y, 500000.0),
            unreal.Vector(x, y, -500000.0),
            object_types, False, [],
            unreal.DrawDebugTrace.NONE)
        if not hit.get_editor_property("bBlockingHit"):
            return None, False
        loc = hit.get_editor_property("Location")
        return loc.z, True

    def nearest_spline_xy(x, y):
        best = None
        steps = 1200
        for i in range(steps + 1):
            p = spline.get_location_at_distance_along_spline(length * i / steps, unreal.SplineCoordinateSpace.WORLD)
            d2 = (p.x - x) ** 2 + (p.y - y) ** 2
            if best is None or d2 < best[0]:
                best = (d2, p)
        return math.sqrt(best[0]), best[1]

    gaps = []
    outliers = []
    for road in roads:
        c = road.get_actor_location()
        z, ok = landscape_z(c.x, c.y)
        label = road.get_actor_label()
        if not ok or z is None:
            outliers.append(f"{label} TRACE_MISS roadz={c.z:.1f}")
            continue
        gap = c.z - z
        gaps.append(gap)
        if gap < 5.0 or gap > 25.0:
            lat, sp = nearest_spline_xy(c.x, c.y)
            outliers.append(
                f"{label} GAP={gap:.3f} ROAD_Z={c.z:.1f} TERR_Z={z:.1f} "
                f"LATERAL_TO_SPLINE={lat:.1f} SPLINE_Z={sp.z:.1f}")

    if gaps:
        gs = sorted(gaps)
        unreal.log(
            f"JPGAP2 COUNT={len(gs)} MIN={gs[0]:.3f} MAX={gs[-1]:.3f} "
            f"MEDIAN={gs[len(gs)//2]:.3f}")
    unreal.log(f"JPGAP2 OUTLIERS={len(outliers)}")
    for line in outliers[:40]:
        unreal.log(f"JPGAP2 OUT {line}")
finally:
    unreal.SystemLibrary.quit_editor()
