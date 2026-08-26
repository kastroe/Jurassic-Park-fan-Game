import math

import unreal


def max_local_slope(spline):
    points = [
        spline.get_location_at_spline_input_key(
            4.0 + step / 100.0, unreal.SplineCoordinateSpace.WORLD
        )
        for step in range(201)
    ]
    maximum = 0.0
    for current, following in zip(points, points[1:]):
        horizontal = math.hypot(following.x - current.x, following.y - current.y)
        if horizontal > 1.0:
            maximum = max(
                maximum,
                math.degrees(math.atan2(abs(following.z - current.z), horizontal)),
            )
    return maximum


try:
    guide = next(
        actor
        for actor in unreal.EditorLevelLibrary.get_all_level_actors()
        if actor.get_actor_label() == "TOUR_RoadGuide"
    )
    spline = guide.get_component_by_class(unreal.SplineComponent)
    tangents = {
        index: spline.get_arrive_tangent_at_spline_point(
            index, unreal.SplineCoordinateSpace.WORLD
        )
        for index in (4, 5, 6)
    }
    best = None
    scales = (0.0, 0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1, 2.4)
    for scale4 in scales:
        for scale5 in scales:
            for scale6 in scales:
                for index, scale in ((4, scale4), (5, scale5), (6, scale6)):
                    tangent = tangents[index]
                    adjusted = unreal.Vector(tangent.x, tangent.y, tangent.z * scale)
                    spline.set_tangents_at_spline_point(
                        index,
                        adjusted,
                        adjusted,
                        unreal.SplineCoordinateSpace.WORLD,
                        False,
                    )
                spline.update_spline()
                slope = max_local_slope(spline)
                if best is None or slope < best[0]:
                    best = (slope, scale4, scale5, scale6)
    unreal.log(
        f"JPTAN_Z_SEARCH MAX_SLOPE={best[0]:.3f} SCALE4={best[1]:.1f} "
        f"SCALE5={best[2]:.1f} SCALE6={best[3]:.1f}"
    )
finally:
    unreal.SystemLibrary.quit_editor()
