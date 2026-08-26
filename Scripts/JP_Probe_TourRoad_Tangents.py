import math

import unreal


try:
    world = unreal.EditorLevelLibrary.get_editor_world()
    guide = next(
        actor
        for actor in unreal.EditorLevelLibrary.get_all_level_actors()
        if actor.get_actor_label() == "TOUR_RoadGuide"
    )
    spline = guide.get_component_by_class(unreal.SplineComponent)
    count = spline.get_number_of_spline_points()
    for waypoint_index, previous_anchor_index, cusp_index in ((5, 4, 6), (11, 10, 12)):
        previous_anchor = spline.get_location_at_spline_point(
            previous_anchor_index, unreal.SplineCoordinateSpace.WORLD
        )
        cusp = spline.get_location_at_spline_point(cusp_index, unreal.SplineCoordinateSpace.WORLD)
        midpoint = unreal.Vector(
            previous_anchor.x + (cusp.x - previous_anchor.x) * 0.5,
            previous_anchor.y + (cusp.y - previous_anchor.y) * 0.5,
            previous_anchor.z + (cusp.z - previous_anchor.z) * 0.5,
        )
        spline.set_location_at_spline_point(
            waypoint_index, midpoint, unreal.SplineCoordinateSpace.WORLD, False
        )
        waypoint_tangent = unreal.Vector(
            (cusp.x - previous_anchor.x) * 0.5,
            (cusp.y - previous_anchor.y) * 0.5,
            (cusp.z - previous_anchor.z) * 0.5,
        )
        spline.set_tangents_at_spline_point(
            waypoint_index,
            waypoint_tangent,
            waypoint_tangent,
            unreal.SplineCoordinateSpace.WORLD,
            False,
        )
        waypoint_before_anchor = spline.get_location_at_spline_point(
            (previous_anchor_index - 1) % count, unreal.SplineCoordinateSpace.WORLD
        )
        anchor_incoming_x = previous_anchor.x - waypoint_before_anchor.x
        anchor_incoming_y = previous_anchor.y - waypoint_before_anchor.y
        anchor_outgoing_x = midpoint.x - previous_anchor.x
        anchor_outgoing_y = midpoint.y - previous_anchor.y
        anchor_incoming_length = (
            anchor_incoming_x * anchor_incoming_x + anchor_incoming_y * anchor_incoming_y
        ) ** 0.5
        anchor_outgoing_length = (
            anchor_outgoing_x * anchor_outgoing_x + anchor_outgoing_y * anchor_outgoing_y
        ) ** 0.5
        anchor_bisector_x = (
            anchor_incoming_x / anchor_incoming_length + anchor_outgoing_x / anchor_outgoing_length
        )
        anchor_bisector_y = (
            anchor_incoming_y / anchor_incoming_length + anchor_outgoing_y / anchor_outgoing_length
        )
        anchor_bisector_length = (
            anchor_bisector_x * anchor_bisector_x + anchor_bisector_y * anchor_bisector_y
        ) ** 0.5
        anchor_tangent_length = min(anchor_incoming_length, anchor_outgoing_length) * 1.35
        previous_anchor_tangent = unreal.Vector(
            anchor_bisector_x / anchor_bisector_length * anchor_tangent_length,
            anchor_bisector_y / anchor_bisector_length * anchor_tangent_length,
            (midpoint.z - waypoint_before_anchor.z) * 0.5,
        )
        spline.set_tangents_at_spline_point(
            previous_anchor_index,
            previous_anchor_tangent,
            previous_anchor_tangent,
            unreal.SplineCoordinateSpace.WORLD,
            False,
        )
        following_waypoint = spline.get_location_at_spline_point(
            (cusp_index + 1) % count, unreal.SplineCoordinateSpace.WORLD
        )
        incoming_x = cusp.x - midpoint.x
        incoming_y = cusp.y - midpoint.y
        outgoing_x = following_waypoint.x - cusp.x
        outgoing_y = following_waypoint.y - cusp.y
        incoming_length = (incoming_x * incoming_x + incoming_y * incoming_y) ** 0.5
        outgoing_length = (outgoing_x * outgoing_x + outgoing_y * outgoing_y) ** 0.5
        bisector_x = incoming_x / incoming_length + outgoing_x / outgoing_length
        bisector_y = incoming_y / incoming_length + outgoing_y / outgoing_length
        bisector_length = (bisector_x * bisector_x + bisector_y * bisector_y) ** 0.5
        tangent_length = (incoming_length + outgoing_length) * 0.59
        cusp_tangent = unreal.Vector(
            bisector_x / bisector_length * tangent_length,
            bisector_y / bisector_length * tangent_length,
            (following_waypoint.z - midpoint.z) * 0.5,
        )
        spline.set_tangents_at_spline_point(
            cusp_index,
            cusp_tangent,
            cusp_tangent,
            unreal.SplineCoordinateSpace.WORLD,
            False,
        )
        next_anchor = spline.get_location_at_spline_point(
            (cusp_index + 2) % count, unreal.SplineCoordinateSpace.WORLD
        )
        following_incoming_x = following_waypoint.x - cusp.x
        following_incoming_y = following_waypoint.y - cusp.y
        following_outgoing_x = next_anchor.x - following_waypoint.x
        following_outgoing_y = next_anchor.y - following_waypoint.y
        following_incoming_length = (
            following_incoming_x * following_incoming_x
            + following_incoming_y * following_incoming_y
        ) ** 0.5
        following_outgoing_length = (
            following_outgoing_x * following_outgoing_x
            + following_outgoing_y * following_outgoing_y
        ) ** 0.5
        following_bisector_x = (
            following_incoming_x / following_incoming_length
            + following_outgoing_x / following_outgoing_length
        )
        following_bisector_y = (
            following_incoming_y / following_incoming_length
            + following_outgoing_y / following_outgoing_length
        )
        following_bisector_length = (
            following_bisector_x * following_bisector_x
            + following_bisector_y * following_bisector_y
        ) ** 0.5
        following_tangent_length = (
            following_incoming_length + following_outgoing_length
        ) * 0.6
        following_tangent = unreal.Vector(
            following_bisector_x / following_bisector_length * following_tangent_length,
            following_bisector_y / following_bisector_length * following_tangent_length,
            (next_anchor.z - cusp.z) * 0.5,
        )
        spline.set_tangents_at_spline_point(
            (cusp_index + 1) % count,
            following_tangent,
            following_tangent,
            unreal.SplineCoordinateSpace.WORLD,
            False,
        )
    spline.update_spline()
    unreal.log(f"JPTAN_PROBE POINTS={count} LENGTH={spline.get_spline_length():.1f}")
    for index in range(count):
        previous_index = (index - 1) % count
        next_index = (index + 1) % count
        previous = spline.get_location_at_spline_point(previous_index, unreal.SplineCoordinateSpace.WORLD)
        current = spline.get_location_at_spline_point(index, unreal.SplineCoordinateSpace.WORLD)
        following = spline.get_location_at_spline_point(next_index, unreal.SplineCoordinateSpace.WORLD)
        arrive = spline.get_arrive_tangent_at_spline_point(index, unreal.SplineCoordinateSpace.WORLD)
        leave = spline.get_leave_tangent_at_spline_point(index, unreal.SplineCoordinateSpace.WORLD)
        incoming = unreal.Vector(current.x - previous.x, current.y - previous.y, 0.0)
        outgoing = unreal.Vector(following.x - current.x, following.y - current.y, 0.0)
        incoming_dot = arrive.x * incoming.x + arrive.y * incoming.y
        outgoing_dot = leave.x * outgoing.x + leave.y * outgoing.y
        tangent_dot = arrive.x * leave.x + arrive.y * leave.y
        unreal.log(
            f"JPTAN_PROBE INDEX={index} POS=({current.x:.0f},{current.y:.0f}) "
            f"ARRIVE=({arrive.x:.0f},{arrive.y:.0f}) LEAVE=({leave.x:.0f},{leave.y:.0f}) "
            f"IN_DOT={incoming_dot:.0f} OUT_DOT={outgoing_dot:.0f} TAN_DOT={tangent_dot:.0f}"
        )

    sample_count = max(1, int(spline.get_spline_length() / 800.0))
    samples = [
        spline.get_location_at_distance_along_spline(
            spline.get_spline_length() * index / sample_count,
            unreal.SplineCoordinateSpace.WORLD,
        )
        for index in range(sample_count)
    ]

    def orientation(a, b, c):
        value = (b.y - a.y) * (c.x - b.x) - (b.x - a.x) * (c.y - b.y)
        if abs(value) < 1.0e-6:
            return 0
        return 1 if value > 0.0 else 2

    def intersects(a, b, c, d):
        return orientation(a, b, c) != orientation(a, b, d) and orientation(c, d, a) != orientation(c, d, b)

    intersections = 0
    for first in range(sample_count):
        first_next = (first + 1) % sample_count
        for second in range(first + 2, sample_count):
            second_next = (second + 1) % sample_count
            if first == 0 and second_next == 0:
                continue
            if intersects(samples[first], samples[first_next], samples[second], samples[second_next]):
                intersections += 1
                unreal.log(
                    f"JPTAN_PROBE INTERSECTION SEGMENTS={first},{second} "
                    f"P1=({samples[first].x:.0f},{samples[first].y:.0f}) "
                    f"P2=({samples[second].x:.0f},{samples[second].y:.0f})"
                )
    unreal.log(f"JPTAN_PROBE INTERSECTION_COUNT={intersections}")

    turns = []
    for index in range(sample_count):
        previous = samples[(index - 1) % sample_count]
        current = samples[index]
        following = samples[(index + 1) % sample_count]
        first_x = current.x - previous.x
        first_y = current.y - previous.y
        second_x = following.x - current.x
        second_y = following.y - current.y
        first_length = (first_x * first_x + first_y * first_y) ** 0.5
        second_length = (second_x * second_x + second_y * second_y) ** 0.5
        if first_length < 1.0 or second_length < 1.0:
            continue
        dot = (first_x * second_x + first_y * second_y) / (first_length * second_length)
        angle = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
        radius = (first_length + second_length) * 0.25 / math.sin(math.radians(angle) * 0.5)
        turns.append((angle, index, current, radius))
    turns.sort(key=lambda item: item[0], reverse=True)
    for angle, index, point, radius in turns[:12]:
        unreal.log(
            f"JPTAN_PROBE TURN={angle:.1f} RADIUS={radius:.0f} SAMPLE={index} "
            f"POS=({point.x:.0f},{point.y:.0f})"
        )
except Exception:
    unreal.log_error("JPTAN_PROBE FAILED")
    raise
finally:
    unreal.SystemLibrary.quit_editor()
