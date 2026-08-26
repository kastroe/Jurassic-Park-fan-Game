import math

import unreal


def vector_between(start, end):
    return unreal.Vector(end.x - start.x, end.y - start.y, end.z - start.z)


def length_2d(vector):
    return math.hypot(vector.x, vector.y)


def bisector_tangent(incoming, outgoing, magnitude, z):
    incoming_length = length_2d(incoming)
    outgoing_length = length_2d(outgoing)
    x = incoming.x / incoming_length + outgoing.x / outgoing_length
    y = incoming.y / incoming_length + outgoing.y / outgoing_length
    direction_length = math.hypot(x, y)
    return unreal.Vector(x / direction_length * magnitude, y / direction_length * magnitude, z)


def local_min_radius(spline, start_key):
    points = [
        spline.get_location_at_spline_input_key(
            start_key + step / 40.0, unreal.SplineCoordinateSpace.WORLD
        )
        for step in range(161)
    ]
    minimum = float("inf")
    for index in range(1, len(points) - 1):
        first = vector_between(points[index - 1], points[index])
        second = vector_between(points[index], points[index + 1])
        first_length = length_2d(first)
        second_length = length_2d(second)
        if first_length < 1.0 or second_length < 1.0:
            continue
        dot = (first.x * second.x + first.y * second.y) / (first_length * second_length)
        angle = math.acos(max(-1.0, min(1.0, dot)))
        if angle < 1.0e-6:
            continue
        radius = (first_length + second_length) * 0.25 / math.sin(angle * 0.5)
        minimum = min(minimum, radius)
    return minimum


def apply_candidate(
    spline,
    cusp_index,
    fraction,
    anchor_scale,
    cusp_scale,
    following_scale,
    following_fraction,
    previous_offset,
    previous_waypoint_scale,
):
    count = spline.get_number_of_spline_points()
    previous_anchor_index = (cusp_index - 2) % count
    waypoint_index = (cusp_index - 1) % count
    following_index = (cusp_index + 1) % count
    next_anchor_index = (cusp_index + 2) % count
    waypoint_before_anchor_index = (previous_anchor_index - 1) % count

    previous_anchor = spline.get_location_at_spline_point(previous_anchor_index, unreal.SplineCoordinateSpace.WORLD)
    cusp = spline.get_location_at_spline_point(cusp_index, unreal.SplineCoordinateSpace.WORLD)
    following = spline.get_location_at_spline_point(following_index, unreal.SplineCoordinateSpace.WORLD)
    next_anchor = spline.get_location_at_spline_point(next_anchor_index, unreal.SplineCoordinateSpace.WORLD)
    if following_fraction is not None:
        following = unreal.Vector(
            cusp.x + (next_anchor.x - cusp.x) * following_fraction,
            cusp.y + (next_anchor.y - cusp.y) * following_fraction,
            cusp.z + (next_anchor.z - cusp.z) * following_fraction,
        )
        spline.set_location_at_spline_point(
            following_index, following, unreal.SplineCoordinateSpace.WORLD, False
        )
    waypoint_before_anchor = spline.get_location_at_spline_point(
        waypoint_before_anchor_index, unreal.SplineCoordinateSpace.WORLD
    )
    waypoint = unreal.Vector(
        previous_anchor.x + (cusp.x - previous_anchor.x) * fraction,
        previous_anchor.y + (cusp.y - previous_anchor.y) * fraction,
        previous_anchor.z + (cusp.z - previous_anchor.z) * fraction,
    )
    chord_x = cusp.x - previous_anchor.x
    chord_y = cusp.y - previous_anchor.y
    chord_length = math.hypot(chord_x, chord_y)
    waypoint.x += -chord_y / chord_length * previous_offset
    waypoint.y += chord_x / chord_length * previous_offset
    spline.set_location_at_spline_point(waypoint_index, waypoint, unreal.SplineCoordinateSpace.WORLD, False)

    anchor_incoming = vector_between(waypoint_before_anchor, previous_anchor)
    anchor_outgoing = vector_between(previous_anchor, waypoint)
    anchor_magnitude = min(length_2d(anchor_incoming), length_2d(anchor_outgoing)) * anchor_scale
    anchor_tangent = bisector_tangent(
        anchor_incoming, anchor_outgoing, anchor_magnitude, (waypoint.z - waypoint_before_anchor.z) * 0.5
    )
    spline.set_tangents_at_spline_point(
        previous_anchor_index, anchor_tangent, anchor_tangent, unreal.SplineCoordinateSpace.WORLD, False
    )

    waypoint_incoming = vector_between(previous_anchor, waypoint)
    waypoint_outgoing = vector_between(waypoint, cusp)
    waypoint_magnitude = (
        length_2d(waypoint_incoming) + length_2d(waypoint_outgoing)
    ) * previous_waypoint_scale
    waypoint_tangent = bisector_tangent(
        waypoint_incoming,
        waypoint_outgoing,
        waypoint_magnitude,
        (cusp.z - previous_anchor.z) * 0.5,
    )
    spline.set_tangents_at_spline_point(
        waypoint_index, waypoint_tangent, waypoint_tangent, unreal.SplineCoordinateSpace.WORLD, False
    )

    cusp_incoming = vector_between(waypoint, cusp)
    cusp_outgoing = vector_between(cusp, following)
    cusp_magnitude = (length_2d(cusp_incoming) + length_2d(cusp_outgoing)) * cusp_scale
    cusp_tangent = bisector_tangent(
        cusp_incoming, cusp_outgoing, cusp_magnitude, (following.z - waypoint.z) * 0.5
    )
    spline.set_tangents_at_spline_point(
        cusp_index, cusp_tangent, cusp_tangent, unreal.SplineCoordinateSpace.WORLD, False
    )

    following_incoming = vector_between(cusp, following)
    following_outgoing = vector_between(following, next_anchor)
    following_magnitude = (
        length_2d(following_incoming) + length_2d(following_outgoing)
    ) * following_scale
    following_tangent = bisector_tangent(
        following_incoming,
        following_outgoing,
        following_magnitude,
        (next_anchor.z - cusp.z) * 0.5,
    )
    spline.set_tangents_at_spline_point(
        following_index, following_tangent, following_tangent, unreal.SplineCoordinateSpace.WORLD, False
    )
    spline.update_spline()


try:
    guide = next(
        actor
        for actor in unreal.EditorLevelLibrary.get_all_level_actors()
        if actor.get_actor_label() == "TOUR_RoadGuide"
    )
    spline = guide.get_component_by_class(unreal.SplineComponent)
    count = spline.get_number_of_spline_points()
    original_positions = [
        spline.get_location_at_spline_point(index, unreal.SplineCoordinateSpace.WORLD)
        for index in range(count)
    ]
    original_tangents = [
        (
            spline.get_arrive_tangent_at_spline_point(index, unreal.SplineCoordinateSpace.WORLD),
            spline.get_leave_tangent_at_spline_point(index, unreal.SplineCoordinateSpace.WORLD),
        )
        for index in range(count)
    ]

    for cusp_index in (6, 12):
        best = None
        fractions = (0.55, 0.6, 0.65) if cusp_index == 6 else (0.55,)
        anchor_scales = (1.3, 1.5, 1.7, 1.9) if cusp_index == 6 else (0.7,)
        cusp_scales = (0.3, 0.4, 0.5) if cusp_index == 6 else (0.55,)
        following_scales = (0.3, 0.4, 0.5) if cusp_index == 6 else (0.55,)
        following_fractions = (None,) if cusp_index == 6 else (0.425,)
        previous_offsets = (-15000.0,) if cusp_index == 6 else (0.0,)
        previous_waypoint_scales = (0.5, 0.6, 0.7) if cusp_index == 6 else (0.5,)
        for fraction in fractions:
            for anchor_scale in anchor_scales:
                for cusp_scale in cusp_scales:
                    for following_scale in following_scales:
                        for following_fraction in following_fractions:
                            for previous_offset in previous_offsets:
                                for previous_waypoint_scale in previous_waypoint_scales:
                                    for index in range(count):
                                        spline.set_location_at_spline_point(
                                            index, original_positions[index], unreal.SplineCoordinateSpace.WORLD, False
                                        )
                                        spline.set_tangents_at_spline_point(
                                            index,
                                            original_tangents[index][0],
                                            original_tangents[index][1],
                                            unreal.SplineCoordinateSpace.WORLD,
                                            False,
                                        )
                                    apply_candidate(
                                        spline,
                                        cusp_index,
                                        fraction,
                                        anchor_scale,
                                        cusp_scale,
                                        following_scale,
                                        following_fraction,
                                        previous_offset,
                                        previous_waypoint_scale,
                                    )
                                    radius = local_min_radius(spline, cusp_index - 2)
                                    if best is None or radius > best[0]:
                                        best = (
                                            radius,
                                            fraction,
                                            anchor_scale,
                                            cusp_scale,
                                            following_scale,
                                            following_fraction,
                                            previous_offset,
                                            previous_waypoint_scale,
                                        )
        unreal.log(
            f"JPTAN_SEARCH CUSP={cusp_index} RADIUS={best[0]:.0f} FRACTION={best[1]:.2f} "
            f"ANCHOR={best[2]:.2f} CUSP_SCALE={best[3]:.2f} FOLLOWING={best[4]:.2f} "
            f"FOLLOWING_FRACTION={best[5]} OFFSET={best[6]:.0f} WAYPOINT={best[7]:.2f}"
        )
except Exception:
    unreal.log_error("JPTAN_SEARCH FAILED")
    raise
finally:
    unreal.SystemLibrary.quit_editor()
