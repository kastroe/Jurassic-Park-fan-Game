import math
import os
import struct
import unreal
import zlib
import inspect


# IMPORTED LANDMARK SITE FIT
#
# This pass preserves both imported landmark meshes as intact actors. It grades
# the real Landscape through the editor spline API, then replaces only its own
# arrival-road namespace. B13/B15/B10 and unrelated park actors are read-only.

DIAGNOSTIC_ONLY = True


def diagnostic_methods(value, terms):
    result = []
    for name in sorted(dir(value)):
        if any(term in name.lower() for term in terms):
            try:
                member = getattr(value, name)
                signature = "unknown"
                if callable(member):
                    try:
                        signature = str(inspect.signature(member))
                    except Exception:
                        signature = "callable; signature unavailable"
                result.append("%s callable=%s signature=%s" % (name, callable(member), signature))
            except Exception as error:
                result.append("%s inaccessible=%s" % (name, error))
    return result


def diagnostic_component_apis():
    actor_class = getattr(unreal, "Actor", None)
    spline_class = getattr(unreal, "SplineComponent", None)
    actor_subsystem_class = getattr(unreal, "EditorActorSubsystem", None)
    if actor_class is not None:
        unreal.log("JP SITE FIT DIAGNOSTIC Actor component_methods=%s" % diagnostic_methods(
            actor_class, ("component", "add", "instance"),
        ))
    else:
        unreal.log("JP SITE FIT DIAGNOSTIC Actor class=False")
    if spline_class is not None:
        unreal.log("JP SITE FIT DIAGNOSTIC SplineComponent ownership_methods=%s" % diagnostic_methods(
            spline_class, ("owner", "outer", "attach", "register", "component", "creation"),
        ))
    else:
        unreal.log("JP SITE FIT DIAGNOSTIC SplineComponent class=False")
    if actor_subsystem_class is not None:
        try:
            actor_subsystem = unreal.get_editor_subsystem(actor_subsystem_class)
            unreal.log("JP SITE FIT DIAGNOSTIC EditorActorSubsystem component_methods=%s" % diagnostic_methods(
                actor_subsystem, ("component", "add", "instance", "register", "attach"),
            ))
        except Exception as error:
            unreal.log_warning("JP SITE FIT DIAGNOSTIC EditorActorSubsystem unavailable: %s" % error)
    else:
        unreal.log("JP SITE FIT DIAGNOSTIC EditorActorSubsystem class=False")


def diagnostic_edit_layer_object(layer, index):
    terms = (
        "name", "guid", "id", "visible", "visibility", "locked", "lock", "height", "weight",
        "alpha", "blend", "edit", "current", "select", "delete", "remove", "rename", "parent", "owner",
    )
    matched = []
    for name in sorted(dir(layer)):
        if any(term in name.lower() for term in terms):
            try:
                member = getattr(layer, name)
                matched.append(name)
                unreal.log("JP SITE FIT DIAGNOSTIC EDIT LAYER DETAIL index=%d member=%s callable=%s" % (
                    index, name, callable(member),
                ))
            except Exception as error:
                unreal.log_warning("JP SITE FIT DIAGNOSTIC EDIT LAYER DETAIL index=%d member=%s inaccessible=%s" % (
                    index, name, error,
                ))

    for accessor_name in ("get_name", "get_path_name", "get_outer"):
        accessor = getattr(layer, accessor_name, None)
        if callable(accessor):
            try:
                value = accessor()
                if accessor_name == "get_outer" and value is not None:
                    value = "%s:%s" % (type(value).__name__, value)
                unreal.log("JP SITE FIT DIAGNOSTIC EDIT LAYER DETAIL index=%d %s=%s" % (
                    index, accessor_name, value,
                ))
            except Exception as error:
                unreal.log_warning("JP SITE FIT DIAGNOSTIC EDIT LAYER DETAIL index=%d %s failed=%s" % (
                    index, accessor_name, error,
                ))
    try:
        unreal.log("JP SITE FIT DIAGNOSTIC EDIT LAYER DETAIL index=%d class=%s" % (
            index, layer.get_class().get_name(),
        ))
    except Exception as error:
        unreal.log_warning("JP SITE FIT DIAGNOSTIC EDIT LAYER DETAIL index=%d class lookup failed=%s" % (index, error))

    discovered_properties = []
    readable_values = {}
    for name in matched:
        try:
            if callable(getattr(layer, name)):
                continue
        except Exception:
            continue
        try:
            value = layer.get_editor_property(name)
            discovered_properties.append(name)
            readable_values[name] = value
            unreal.log("JP SITE FIT DIAGNOSTIC EDIT LAYER PROPERTY index=%d name=%s value=%s" % (
                index, name, value,
            ))
        except Exception as error:
            unreal.log("JP SITE FIT DIAGNOSTIC EDIT LAYER PROPERTY index=%d name=%s unreadable=%s" % (
                index, name, error,
            ))
    unreal.log("JP SITE FIT DIAGNOSTIC EDIT LAYER DISCOVERED_PROPERTIES index=%d properties=%s" % (
        index, discovered_properties,
    ))
    return readable_values


def run_runtime_diagnostic():
    unreal.log("JP SITE FIT DIAGNOSTIC START: no Landscape or actor mutation will run")

    actor_subsystem_class = getattr(unreal, "EditorActorSubsystem", None)
    landscape_proxy_class = getattr(unreal, "LandscapeProxy", None)
    landscape_class = getattr(unreal, "Landscape", None)
    landscape = None
    if actor_subsystem_class is not None:
        actor_subsystem = unreal.get_editor_subsystem(actor_subsystem_class)
        actors = list(actor_subsystem.get_all_level_actors())
        unreal.log("JP SITE FIT DIAGNOSTIC level_actor_count=%d" % len(actors))
        for actor in actors:
            if landscape_class is not None and isinstance(actor, landscape_class):
                landscape = actor
                break
            if landscape_proxy_class is not None and isinstance(actor, landscape_proxy_class):
                try:
                    landscape = actor.get_landscape_actor() or actor
                except Exception:
                    landscape = actor
                break

    if landscape is None:
        unreal.log_warning("JP SITE FIT DIAGNOSTIC Landscape actor not found")
    else:
        unreal.log("JP SITE FIT DIAGNOSTIC Landscape class=%s label=%s" % (landscape.get_class().get_name(), landscape.get_actor_label()))
        unreal.log("JP SITE FIT DIAGNOSTIC Landscape methods=%s" % diagnostic_methods(landscape, (
            "spline", "height", "layer", "edit", "render", "undo", "copy", "duplicate",
        )))
        for method_name in ("editor_apply_spline",):
            method = getattr(landscape, method_name, None)
            try:
                signature = str(inspect.signature(method)) if callable(method) else "not callable"
            except Exception:
                signature = "callable; signature unavailable" if callable(method) else "not callable"
            unreal.log("JP SITE FIT DIAGNOSTIC Landscape API %s present=%s callable=%s signature=%s" % (
                method_name, method is not None, callable(method), signature,
            ))
        unreal.log("JP SITE FIT DIAGNOSTIC Landscape layer/edit methods=%s" % diagnostic_methods(landscape, (
            "create", "add", "remove", "delete", "layer", "edit", "current", "select",
        )))
        get_layers = getattr(landscape, "get_edit_layers_bp", None)
        get_layer_by_name = getattr(landscape, "get_edit_layer_by_name_bp", None)
        layer_names = []
        if callable(get_layers):
            try:
                layers = list(get_layers())
                unreal.log("JP SITE FIT DIAGNOSTIC EDIT LAYERS count=%d" % len(layers))
                for index, layer in enumerate(layers):
                    layer_values = diagnostic_edit_layer_object(layer, index)
                    for name_key in ("layer_name", "name"):
                        if name_key in layer_values:
                            layer_names.append(str(layer_values[name_key]))
            except Exception as error:
                unreal.log_warning("JP SITE FIT DIAGNOSTIC get_edit_layers_bp failed: %s" % error)
        else:
            unreal.log("JP SITE FIT DIAGNOSTIC get_edit_layers_bp present=False callable=False")
        if callable(get_layer_by_name):
            for layer_name in layer_names:
                for query in (layer_name, unreal.Name(layer_name)):
                    try:
                        result = get_layer_by_name(query)
                        unreal.log("JP SITE FIT DIAGNOSTIC get_edit_layer_by_name_bp query=%s result=%s class=%s" % (
                            query,
                            result,
                            type(result).__name__,
                        ))
                    except Exception as error:
                        unreal.log_warning("JP SITE FIT DIAGNOSTIC get_edit_layer_by_name_bp query=%s failed: %s" % (query, error))
        else:
            unreal.log("JP SITE FIT DIAGNOSTIC get_edit_layer_by_name_bp present=False callable=False")

        edit_layer_class = getattr(unreal, "LandscapeEditLayer", None)
        if edit_layer_class is None:
            unreal.log("JP SITE FIT DIAGNOSTIC LandscapeEditLayer class=False")
        else:
            unreal.log("JP SITE FIT DIAGNOSTIC LandscapeEditLayer class_methods=%s" % diagnostic_methods(edit_layer_class, (
                "name", "guid", "id", "visible", "visibility", "locked", "lock", "height", "weight", "alpha",
                "blend", "edit", "current", "select", "delete", "remove", "rename", "parent", "owner",
            )))
        unreal.log("JP SITE FIT DIAGNOSTIC Landscape focused edit-layer methods=%s" % diagnostic_methods(landscape, (
            "set_edit", "active", "current_layer", "edit_layer", "layer_guid", "layer_name",
        )))

    editor_subsystem_class = getattr(unreal, "LandscapeEditorSubsystem", None)
    if editor_subsystem_class is None:
        unreal.log("JP SITE FIT DIAGNOSTIC LandscapeEditorSubsystem class=False")
    else:
        try:
            editor_subsystem = unreal.get_editor_subsystem(editor_subsystem_class)
            unreal.log("JP SITE FIT DIAGNOSTIC LandscapeEditorSubsystem methods=%s" % diagnostic_methods(editor_subsystem, (
                "landscape", "layer", "edit", "height", "flatten", "tool", "brush", "target", "undo",
            )))
        except Exception as error:
            unreal.log_warning("JP SITE FIT DIAGNOSTIC LandscapeEditorSubsystem unavailable: %s" % error)

    diagnostic_component_apis()
    unreal.log("JP SITE FIT DIAGNOSTIC COMPLETE: script intentionally exits before mutation")


if DIAGNOSTIC_ONLY:
    run_runtime_diagnostic()
    raise SystemExit("JP SITE FIT DIAGNOSTIC ONLY")

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assetlib = unreal.EditorAssetLibrary

VC_LABEL = "B16_JP_VC_Model"
GATE_LABEL = "B17_JP_GATE_Model"
SITE_PREFIX = "B18_JP_ARRIVAL_"
STAGING_PREFIX = "B18_JP_ARRIVAL_Staging_"
BACKUP_PREFIX = "B18_JP_ARRIVAL_Backup_"

HEIGHTMAP = os.path.join(
    unreal.Paths.project_dir(),
    "Content",
    "JPBlockout",
    "JP_Island_Heightmap_2017_v05.png",
)
LANDSCAPE_MIN_X = -100800.0
LANDSCAPE_MIN_Y = -100800.0
LANDSCAPE_SPACING = 100.0
LANDSCAPE_Z_SCALE = 100.0
LANDSCAPE_ACTOR_Z = 0.0
GROUND_CLEARANCE = 25.0
MAX_SAMPLE_SPREAD = 1200.0
ROAD_WIDTH = 1600.0
ROAD_THICKNESS = 24.0
ROAD_OVERLAP = 120.0
GATE_OPENING_LOCAL_YAW = 90.0
LANDSCAPE_GRADE_PREFIX = "B18_JP_ARRIVAL_LandscapeGrade_"
LANDSCAPE_GRADE_ROWS = 11
LANDSCAPE_GRADE_SPACING = 450.0
LANDSCAPE_GRADE_FALLOFF = 900.0
LANDSCAPE_ROAD_FALLOFF = 650.0
TERRAIN_MAPPING_TRUSTED = True
LANDSCAPE_EDIT_STARTED = False

unreal.log(
    "JP SITE FIT START: heightmap=%s mapping=min(%.1f,%.1f) xy_spacing=%.1f z_scale=%.1f actor_z=%.1f; fitting is advisory"
    % (
        HEIGHTMAP,
        LANDSCAPE_MIN_X,
        LANDSCAPE_MIN_Y,
        LANDSCAPE_SPACING,
        LANDSCAPE_Z_SCALE,
        LANDSCAPE_ACTOR_Z,
    )
)

cube = assetlib.load_asset("/Engine/BasicShapes/Cube.Cube")
asphalt = assetlib.load_asset("/Game/JPGenerated/Materials/M_JP_Asphalt")
if not cube or not asphalt:
    raise RuntimeError("Required arrival-road mesh/material is missing.")


def all_actors():
    return list(actor_sub.get_all_level_actors())


def exact(label):
    return [actor for actor in all_actors() if actor.get_actor_label() == label]


def by_prefix(prefix):
    return [actor for actor in all_actors() if actor.get_actor_label().startswith(prefix)]


def bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return (
        origin.x - extent.x,
        origin.x + extent.x,
        origin.y - extent.y,
        origin.y + extent.y,
        origin.z - extent.z,
        origin.z + extent.z,
    )


def snapshot(actor):
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    return (
        actor.get_actor_label(),
        (location.x, location.y, location.z),
        (rotation.pitch, rotation.yaw, rotation.roll),
        (scale.x, scale.y, scale.z),
    )


def assert_intact(before, actor, name, allow_z_delta=True):
    after = snapshot(actor)
    if before[0] != after[0]:
        raise RuntimeError("%s label changed" % name)
    if before[3] != after[3]:
        raise RuntimeError("%s scale changed" % name)
    if before[2] != after[2]:
        raise RuntimeError("%s rotation changed" % name)
    if abs(before[1][0] - after[1][0]) > 0.01 or abs(before[1][1] - after[1][1]) > 0.01:
        raise RuntimeError("%s XY position changed" % name)
    if not allow_z_delta and abs(before[1][2] - after[1][2]) > 0.01:
        raise RuntimeError("%s location changed" % name)


def read_heightmap(path):
    with open(path, "rb") as stream:
        data = stream.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("Invalid heightmap PNG")
    position = 8
    compressed = bytearray()
    width = height = bit_depth = color_type = None
    while position < len(data):
        length = struct.unpack(">I", data[position:position + 4])[0]
        kind = data[position + 4:position + 8]
        chunk = data[position + 8:position + 8 + length]
        position += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", chunk)
        elif kind == b"IDAT":
            compressed.extend(chunk)
        elif kind == b"IEND":
            break
    if bit_depth != 16 or color_type != 0:
        raise RuntimeError("Expected a 16-bit grayscale heightmap")

    raw = zlib.decompress(bytes(compressed))
    stride = width * 2
    rows = []
    previous = bytearray(stride)
    offset = 0

    def paeth(a, b, c):
        estimate = a + b - c
        pa = abs(estimate - a)
        pb = abs(estimate - b)
        pc = abs(estimate - c)
        if pa <= pb and pa <= pc:
            return a
        return b if pb <= pc else c

    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        scan = bytearray(raw[offset:offset + stride])
        offset += stride
        reconstructed = bytearray(stride)
        for index in range(stride):
            left = reconstructed[index - 2] if index >= 2 else 0
            up = previous[index]
            upper_left = previous[index - 2] if index >= 2 else 0
            value = scan[index]
            if filter_type == 1:
                value = (value + left) & 255
            elif filter_type == 2:
                value = (value + up) & 255
            elif filter_type == 3:
                value = (value + ((left + up) // 2)) & 255
            elif filter_type == 4:
                value = (value + paeth(left, up, upper_left)) & 255
            elif filter_type != 0:
                raise RuntimeError("Unsupported PNG filter")
            reconstructed[index] = value
        rows.append([(reconstructed[index] << 8) | reconstructed[index + 1] for index in range(0, stride, 2)])
        previous = reconstructed
    return width, height, rows


HM_WIDTH = HM_HEIGHT = None
HEIGHTS = None
if os.path.exists(HEIGHTMAP):
    try:
        HM_WIDTH, HM_HEIGHT, HEIGHTS = read_heightmap(HEIGHTMAP)
    except Exception as error:
        unreal.log_warning("JP SITE FIT: heightmap could not be read; terrain fitting disabled: %s" % error)
else:
    unreal.log_warning("JP SITE FIT: heightmap is missing; terrain fitting disabled: %s" % HEIGHTMAP)


def terrain_z(x, y):
    if not TERRAIN_MAPPING_TRUSTED or HEIGHTS is None:
        return None
    fx = (x - LANDSCAPE_MIN_X) / LANDSCAPE_SPACING
    fy = (y - LANDSCAPE_MIN_Y) / LANDSCAPE_SPACING
    if fx < 0.0 or fy < 0.0 or fx > HM_WIDTH - 1.001 or fy > HM_HEIGHT - 1.001:
        return None
    x0 = int(fx)
    y0 = int(fy)
    x1 = min(HM_WIDTH - 1, x0 + 1)
    y1 = min(HM_HEIGHT - 1, y0 + 1)
    tx = fx - x0
    ty = fy - y0
    value = (
        HEIGHTS[y0][x0] * (1 - tx) * (1 - ty)
        + HEIGHTS[y0][x1] * tx * (1 - ty)
        + HEIGHTS[y1][x0] * (1 - tx) * ty
        + HEIGHTS[y1][x1] * tx * ty
    )
    return LANDSCAPE_ACTOR_Z + (float(value) - 32768.0) * LANDSCAPE_Z_SCALE / 128.0


def inspect_landscape_transform():
    global TERRAIN_MAPPING_TRUSTED
    landscape_actors = []
    for actor in all_actors():
        class_name = actor.get_class().get_name()
        if class_name in ("Landscape", "LandscapeStreamingProxy"):
            landscape_actors.append(actor)
    if not landscape_actors:
        unreal.log_warning("JP SITE FIT: no Landscape actor was enumerable; using verified import mapping only")
        return
    unreal.log(
        "JP SITE FIT: found %d landscape actor(s); expected import transform is location=(0,0,0), scale=(1,1,1), XY origin=(%.1f,%.1f)"
        % (len(landscape_actors), LANDSCAPE_MIN_X, LANDSCAPE_MIN_Y)
    )
    root_landscapes = [actor for actor in landscape_actors if actor.get_class().get_name() == "Landscape"]
    for actor in root_landscapes:
        location = actor.get_actor_location()
        scale = actor.get_actor_scale3d()
        if (
            abs(location.x) > 1.0
            or abs(location.y) > 1.0
            or abs(location.z) > 1.0
            or abs(scale.x - 1.0) > 0.001
            or abs(scale.y - 1.0) > 0.001
        ):
            TERRAIN_MAPPING_TRUSTED = False
            unreal.log_warning(
                "JP SITE FIT: landscape transform differs from verified heightmap mapping; terrain fitting disabled, road will use live-bound fallback"
            )
    for actor in landscape_actors[:8]:
        location = actor.get_actor_location()
        scale = actor.get_actor_scale3d()
        origin, extent = actor.get_actor_bounds(False)
        unreal.log(
            "JP SITE FIT LANDSCAPE: %s loc=(%.1f,%.1f,%.1f) scale=(%.4f,%.4f,%.4f) bounds_center=(%.1f,%.1f,%.1f) bounds_extent=(%.1f,%.1f,%.1f)"
            % (
                actor.get_actor_label(),
                location.x,
                location.y,
                location.z,
                scale.x,
                scale.y,
                scale.z,
                origin.x,
                origin.y,
                origin.z,
                extent.x,
                extent.y,
                extent.z,
            )
        )


inspect_landscape_transform()


def find_landscape():
    for actor in all_actors():
        if isinstance(actor, unreal.Landscape):
            return actor
    for actor in all_actors():
        if isinstance(actor, unreal.LandscapeProxy):
            try:
                landscape = actor.get_landscape_actor()
                if landscape:
                    return landscape
            except Exception:
                pass
    return None


def make_spline_actor(label, points):
    actor = actor_sub.spawn_actor_from_class(unreal.Actor, unreal.Vector(), unreal.Rotator())
    try:
        actor.set_actor_label(LANDSCAPE_GRADE_PREFIX + label)
        spline = unreal.new_object(unreal.SplineComponent, outer=actor)
        spline.register_component()
        spline.clear_spline_points(False)
        for point in points:
            spline.add_spline_point(point, unreal.SplineCoordinateSpace.WORLD, False)
        spline.update_spline()
        return actor, spline
    except Exception:
        actor_sub.destroy_actor(actor)
        raise


def apply_landscape_spline(landscape, label, points, width, falloff, subdivisions=16):
    global LANDSCAPE_EDIT_STARTED
    actor, spline = make_spline_actor(label, points)
    try:
        if not LANDSCAPE_EDIT_STARTED:
            LANDSCAPE_EDIT_STARTED = True
            unreal.log("JP SITE FIT LANDSCAPE EDIT START")
        landscape.editor_apply_spline(
            spline,
            width,
            width,
            falloff,
            falloff,
            0.0,
            0.0,
            subdivisions,
            True,
            True,
            None,
            unreal.Name("None"),
        )
    finally:
        actor_sub.destroy_actor(actor)


def trace_landscape_z(x, y, ignored):
    world = unreal.EditorLevelLibrary.get_editor_world()
    hit = unreal.SystemLibrary.line_trace_single(
        world,
        unreal.Vector(x, y, 150000.0),
        unreal.Vector(x, y, -150000.0),
        unreal.TraceTypeQuery.ECC_VISIBILITY,
        False,
        ignored,
        unreal.DrawDebugTrace.NONE,
        True,
    )
    if hit is None:
        return None
    for property_name in ("impact_point", "location"):
        try:
            value = getattr(hit, property_name)
            return float(value.z)
        except Exception:
            try:
                value = hit.get_editor_property(property_name)
                return float(value.z)
            except Exception:
                pass
    return None


def grade_visitor_site(landscape, vc, vc_center, route_x, route_y, finished_z, gate_z, vc_front_z, road_height):
    min_x, max_x, min_y, max_y, _, _ = bounds(vc)
    radius_x = (max_x - min_x) * 0.5 + 1400.0
    radius_y = (max_y - min_y) * 0.5 + 1000.0
    site_center_x = vc_center.x - route_x * 650.0
    site_center_y = vc_center.y - route_y * 650.0
    perpendicular_x = -route_y
    perpendicular_y = route_x
    row_half = (LANDSCAPE_GRADE_ROWS - 1) * 0.5
    for row in range(LANDSCAPE_GRADE_ROWS):
        offset = (row - row_half) * LANDSCAPE_GRADE_SPACING
        normalized = min(1.0, abs(offset) / radius_y)
        chord = radius_x * math.sqrt(max(0.0, 1.0 - normalized * normalized))
        start = unreal.Vector(
            site_center_x - route_x * chord + perpendicular_x * offset,
            site_center_y - route_y * chord + perpendicular_y * offset,
            finished_z,
        )
        end = unreal.Vector(
            site_center_x + route_x * chord + perpendicular_x * offset,
            site_center_y + route_y * chord + perpendicular_y * offset,
            finished_z,
        )
        apply_landscape_spline(
            landscape,
            "VC_Oval_%02d" % row,
            (start, end),
            LANDSCAPE_GRADE_SPACING * 0.5,
            LANDSCAPE_GRADE_FALLOFF,
            24,
        )

    forecourt_x = vc_center.x + route_x * 500.0
    forecourt_y = vc_center.y + route_y * 500.0
    road_points = []
    for index in range(5):
        blend = index / 4.0
        road_z = vc_front_z if blend == 0.0 else gate_z if blend == 1.0 else road_height(1.0 - blend, gate_z)
        road_points.append(
            unreal.Vector(
                forecourt_x + (vc_center.x - route_x * 5000.0 - forecourt_x) * blend,
                forecourt_y + (vc_center.y - route_y * 5000.0 - forecourt_y) * blend,
                road_z,
            )
        )
    apply_landscape_spline(
        landscape,
        "Arrival_Grade",
        road_points,
        ROAD_WIDTH * 0.5,
        LANDSCAPE_ROAD_FALLOFF,
        32,
    )
    return site_center_x, site_center_y, radius_x, radius_y


def validate_visitor_landscape(vc, finished_z, ignored):
    min_x, max_x, min_y, max_y, _, _ = bounds(vc)
    samples = []
    for ix in range(7):
        x = min_x + (max_x - min_x) * ix / 6.0
        for iy in range(7):
            y = min_y + (max_y - min_y) * iy / 6.0
            value = trace_landscape_z(x, y, ignored)
            if value is None:
                return False, samples
            samples.append(value)
    return max(samples) <= finished_z + 100.0, samples


vc_matches = exact(VC_LABEL)
gate_matches = exact(GATE_LABEL)
if len(vc_matches) != 1 or len(gate_matches) != 1:
    raise RuntimeError("Expected exactly one imported Visitor Center and gate actor.")
vc = vc_matches[0]
gate = gate_matches[0]
vc_before = snapshot(vc)
gate_before = snapshot(gate)


def center(actor):
    min_x, max_x, min_y, max_y, _, _ = bounds(actor)
    return unreal.Vector((min_x + max_x) * 0.5, (min_y + max_y) * 0.5, 0.0)


def robust_terrain_samples(actor):
    min_x, max_x, min_y, max_y, min_z, _ = bounds(actor)
    points = (
        (min_x, min_y),
        (min_x, (min_y + max_y) * 0.5),
        (min_x, max_y),
        ((min_x + max_x) * 0.5, min_y),
        ((min_x + max_x) * 0.5, (min_y + max_y) * 0.5),
        ((min_x + max_x) * 0.5, max_y),
        (max_x, min_y),
        (max_x, (min_y + max_y) * 0.5),
        (max_x, max_y),
    )
    samples = []
    for x, y in points:
        value = terrain_z(x, y)
        unreal.log(
            "JP SITE FIT SAMPLE: %s xy=(%.1f,%.1f) terrain_z=%s model_bottom_min_z=%.1f"
            % (actor.get_actor_label(), x, y, "None" if value is None else "%.1f" % value, min_z)
        )
        if value is not None:
            samples.append(value)
    if len(samples) < 5:
        return min_z, None, samples
    ordered = sorted(samples)
    median = ordered[len(ordered) // 2]
    deviations = sorted(abs(value - median) for value in samples)
    mad = deviations[len(deviations) // 2]
    inliers = [value for value in samples if abs(value - median) <= max(250.0, mad * 3.0)]
    if len(inliers) < 5 or max(inliers) - min(inliers) > MAX_SAMPLE_SPREAD:
        return min_z, None, samples
    inliers.sort()
    return min_z, inliers[len(inliers) // 2], samples


def restore_transform(actor, saved):
    location = saved[1]
    rotation = saved[2]
    scale = saved[3]
    actor.set_actor_location(unreal.Vector(*location), False, False)
    actor.set_actor_rotation(unreal.Rotator(*rotation), False)
    actor.set_actor_scale3d(unreal.Vector(*scale))


def actor_center_z(actor):
    return bounds(actor)[4]


vc_center = center(vc)
gate_center = center(gate)
old_vc_bounds = bounds(vc)
old_gate_bounds = bounds(gate)
road_reference = [actor for actor in by_prefix(SITE_PREFIX) if "Road_" in actor.get_actor_label()]
route_x = vc_center.x - gate_center.x
route_y = vc_center.y - gate_center.y
route_length = math.sqrt(route_x * route_x + route_y * route_y)
if route_length < 1000.0:
    raise RuntimeError("Imported landmarks are too close for a site route.")
route_x /= route_length
route_y /= route_length

road_heading = math.degrees(math.atan2(route_y, route_x))
road_profile = []
if road_reference:
    projected = []
    for actor in road_reference:
        point = center(actor)
        projection = (point.x - gate_center.x) * route_x + (point.y - gate_center.y) * route_y
        projected.append((projection, bounds(actor)[5]))
    projected.sort()
    if len(projected) >= 2:
        first = center(min(road_reference, key=lambda actor: (center(actor).x - gate_center.x) * route_x + (center(actor).y - gate_center.y) * route_y))
        last = center(max(road_reference, key=lambda actor: (center(actor).x - gate_center.x) * route_x + (center(actor).y - gate_center.y) * route_y))
        heading_x = last.x - first.x
        heading_y = last.y - first.y
        if heading_x * route_x + heading_y * route_y < 0.0:
            heading_x = -heading_x
            heading_y = -heading_y
        road_heading = math.degrees(math.atan2(heading_y, heading_x))
    for projection, top_z in projected:
        road_profile.append((max(0.0, min(1.0, projection / route_length)), top_z))

unreal.log(
    "JP SITE FIT LIVE: B16 center=(%.1f,%.1f) bounds_min_z=%.1f B17 center=(%.1f,%.1f) bounds_min_z=%.1f B18_reference_segments=%d road_heading=%.1f"
    % (vc_center.x, vc_center.y, old_vc_bounds[4], gate_center.x, gate_center.y, old_gate_bounds[4], len(road_reference), road_heading)
)


def profile_z(t, fallback):
    if not road_profile:
        return fallback
    if t <= road_profile[0][0]:
        return road_profile[0][1]
    if t >= road_profile[-1][0]:
        return road_profile[-1][1]
    for index in range(1, len(road_profile)):
        t0, z0 = road_profile[index - 1]
        t1, z1 = road_profile[index]
        if t <= t1:
            blend = (t - t0) / max(0.001, t1 - t0)
            return z0 + (z1 - z0) * blend
    return fallback


old_vc = snapshot(vc)
old_gate = snapshot(gate)


def log_live_actor(actor, name):
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    min_x, max_x, min_y, max_y, min_z, max_z = bounds(actor)
    unreal.log(
        "JP SITE FIT LIVE TRANSFORM: %s loc=(%.1f,%.1f,%.1f) rot=(%.1f,%.1f,%.1f) scale=(%.6f,%.6f,%.6f) bounds=(x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f)"
        % (
            name,
            location.x,
            location.y,
            location.z,
            rotation.pitch,
            rotation.yaw,
            rotation.roll,
            scale.x,
            scale.y,
            scale.z,
            min_x,
            max_x,
            min_y,
            max_y,
            min_z,
            max_z,
        )
    )


log_live_actor(vc, "B16_JP_VC_Model")
log_live_actor(gate, "B17_JP_GATE_Model")
unreal.log(
    "JP SITE FIT GATE FRONT: imported local +Y opening direction currently has world yaw=%.1f; target travel heading=%.1f"
    % (old_gate[2][1] + GATE_OPENING_LOCAL_YAW, road_heading)
)
old_vc_bottom, _, _ = robust_terrain_samples(vc)
finished_z = old_vc_bottom - GROUND_CLEARANCE
landscape = find_landscape()
if landscape is None or not callable(getattr(landscape, "editor_apply_spline", None)):
    raise RuntimeError("Direct Landscape editor spline modification is unavailable; refusing cube/platform fallback.")
if (
    not callable(getattr(unreal, "new_object", None))
    or not hasattr(unreal, "SplineComponent")
    or not hasattr(unreal, "SplineCoordinateSpace")
):
    raise RuntimeError("UE Python spline component creation is unavailable; refusing cube/platform fallback.")
landscape_ignored = [vc, gate] + by_prefix(SITE_PREFIX) + by_prefix(LANDSCAPE_GRADE_PREFIX)
grade_visitor_site(
    landscape,
    vc,
    vc_center,
    route_x,
    route_y,
    finished_z,
    profile_z(0.0, old_gate_bounds[5]),
    finished_z,
    profile_z,
)
landscape_ignored = [
    actor
    for actor in all_actors()
    if not isinstance(actor, unreal.LandscapeProxy)
]
terrain_valid, terrain_samples = validate_visitor_landscape(vc, finished_z, landscape_ignored)
unreal.log(
    "JP SITE FIT LANDSCAPE GRADE: target_z=%.1f samples=%s min=%.1f max=%.1f valid=%s"
    % (
        finished_z,
        len(terrain_samples),
        min(terrain_samples) if terrain_samples else float("nan"),
        max(terrain_samples) if terrain_samples else float("nan"),
        terrain_valid,
    )
)
if not terrain_valid:
    raise RuntimeError("Landscape grade validation failed; no automatic Landscape restore is available.")

vc_min_x, vc_max_x, vc_min_y, vc_max_y, vc_min_z, _ = bounds(vc)

# The import fit established the gate span on world Y at yaw 90 degrees. Its
# opening is therefore the imported local +Y axis. Align that axis with travel,
# choosing the sign that faces the Visitor Center.
try:
    gate_yaw = road_heading - GATE_OPENING_LOCAL_YAW
    opening_x = math.cos(math.radians(gate_yaw + GATE_OPENING_LOCAL_YAW))
    opening_y = math.sin(math.radians(gate_yaw + GATE_OPENING_LOCAL_YAW))
    if opening_x * route_x + opening_y * route_y < 0.0:
        gate_yaw += 180.0
    gate.set_actor_rotation(unreal.Rotator(0.0, gate_yaw, 0.0), False)
    gate_after_bounds = bounds(gate)
    gate_road_top = profile_z(0.0, gate_after_bounds[4] + GROUND_CLEARANCE)
    gate_location = gate.get_actor_location()
    gate_delta = gate_road_top - gate_after_bounds[4]
    gate.set_actor_location(unreal.Vector(gate_location.x, gate_location.y, gate_location.z + gate_delta), False, False)
except Exception:
    restore_transform(gate, old_gate)
    raise

assert_intact(vc_before, vc, "B16 Visitor Center")
if snapshot(gate)[3] != old_gate[3]:
    raise RuntimeError("B17 gate scale changed")
if abs(snapshot(gate)[1][0] - old_gate[1][0]) > 0.01 or abs(snapshot(gate)[1][1] - old_gate[1][1]) > 0.01:
    raise RuntimeError("B17 gate XY position changed")

gate_center = center(gate)
vc_center = center(vc)
direction_x = vc_center.x - gate_center.x
direction_y = vc_center.y - gate_center.y
distance = math.sqrt(direction_x * direction_x + direction_y * direction_y)
direction_x /= distance
direction_y /= distance
gate_min_x, gate_max_x, gate_min_y, gate_max_y, _, _ = bounds(gate)
vc_min_x, vc_max_x, vc_min_y, vc_max_y, _, _ = bounds(vc)
gate_depth = abs(direction_x) * (gate_max_x - gate_min_x) * 0.5 + abs(direction_y) * (gate_max_y - gate_min_y) * 0.5
vc_clearance = abs(direction_x) * (vc_max_x - vc_min_x) * 0.5 + abs(direction_y) * (vc_max_y - vc_min_y) * 0.5 + 500.0
start_x = gate_center.x - direction_x * (gate_depth + 800.0)
start_y = gate_center.y - direction_y * (gate_depth + 800.0)
end_x = vc_center.x - direction_x * vc_clearance
end_y = vc_center.y - direction_y * vc_clearance
usable_length = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)
segment_count = max(6, min(16, int(usable_length / 1800.0) + 1))
vc_road_top = finished_z

for actor in by_prefix(STAGING_PREFIX):
    actor_sub.destroy_actor(actor)

staged = []

try:
    for index in range(segment_count):
        t0 = max(-0.08, index / float(segment_count) - ROAD_OVERLAP / usable_length)
        t1 = min(1.0, (index + 1) / float(segment_count) + ROAD_OVERLAP / usable_length)
        p0_x = start_x + (end_x - start_x) * t0
        p0_y = start_y + (end_y - start_y) * t0
        p1_x = start_x + (end_x - start_x) * t1
        p1_y = start_y + (end_y - start_y) * t1
        dx = p1_x - p0_x
        dy = p1_y - p0_y
        length = math.sqrt(dx * dx + dy * dy)
        mid_x = (p0_x + p1_x) * 0.5
        mid_y = (p0_y + p1_y) * 0.5
        midpoint_t = max(0.0, min(1.0, (t0 + t1) * 0.5))
        fallback_z = gate_road_top + (vc_road_top - gate_road_top) * midpoint_t
        top_z = profile_z(midpoint_t, fallback_z)
        if midpoint_t > 0.90:
            top_z = vc_road_top
        spawn_actor = actor_sub.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(mid_x, mid_y, top_z - ROAD_THICKNESS * 0.5),
            unreal.Rotator(0.0, math.degrees(math.atan2(dy, dx)), 0.0),
        )
        spawn_actor.set_actor_label(STAGING_PREFIX + "Road_%02d" % index)
        spawn_actor.static_mesh_component.set_static_mesh(cube)
        spawn_actor.static_mesh_component.set_material(0, asphalt)
        spawn_actor.set_actor_scale3d(unreal.Vector(length / 100.0, ROAD_WIDTH / 100.0, ROAD_THICKNESS / 100.0))
        staged.append(spawn_actor)
except Exception:
    for actor in staged:
        actor_sub.destroy_actor(actor)
    restore_transform(gate, old_gate)
    raise

if len(staged) != segment_count:
    for actor in staged:
        actor_sub.destroy_actor(actor)
    restore_transform(vc, old_vc)
    restore_transform(gate, old_gate)
    raise RuntimeError("Arrival road staging is incomplete; no automatic Landscape restore is available.")

previous_site = []
try:
    for index, actor in enumerate(all_actors()):
        label = actor.get_actor_label()
        if label.startswith(SITE_PREFIX) and not label.startswith(STAGING_PREFIX):
            previous_site.append((actor, label))
            actor.set_actor_label(BACKUP_PREFIX + "%03d" % index)
    for actor in all_actors():
        if actor.get_actor_label().startswith(STAGING_PREFIX):
            actor.set_actor_label(SITE_PREFIX + actor.get_actor_label()[len(STAGING_PREFIX):])
    if len(by_prefix(SITE_PREFIX)) != len(staged):
        raise RuntimeError("Final B18 site actor count is incorrect.")
    for actor in all_actors():
        if actor.get_actor_label().startswith(BACKUP_PREFIX):
            actor_sub.destroy_actor(actor)
except Exception:
    for actor in staged:
        actor_sub.destroy_actor(actor)
    for actor, old_label in previous_site:
        actor.set_actor_label(old_label)
    restore_transform(vc, old_vc)
    restore_transform(gate, old_gate)
    raise

try:
    save_result = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    if save_result is not True:
        raise RuntimeError("Primary level save did not return True.")
except Exception:
    if unreal.EditorLevelLibrary.save_current_level() is not True:
        raise RuntimeError("Level save failed after site correction.")

final_vc = vc.get_actor_location()
final_gate = gate.get_actor_location()
final_gate_rotation = gate.get_actor_rotation()
unreal.log(
    "JP SITE FIT COMPLETE: B16 location=(%.1f,%.1f,%.1f) landscape_grade_z=%.1f B17 yaw=%.1f location=(%.1f,%.1f,%.1f) B18 road_heading=%.1f road_segments=%d; landscape modified, temporary platforms removed"
    % (
        final_vc.x,
        final_vc.y,
        final_vc.z,
        finished_z,
        final_gate_rotation.yaw,
        final_gate.x,
        final_gate.y,
        final_gate.z,
        road_heading,
        segment_count,
    )
)
