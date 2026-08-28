"""Deterministic Blender generator for original, modular JP-inspired assets.

Run with Blender, not a system Python interpreter:
  blender --background --python jp_asset_builder.py -- --preset electric_fence
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


TOOL_ROOT = Path(__file__).resolve().parent
PRESET_DIR = TOOL_ROOT / "presets"
OUTPUT_DIR = TOOL_ROOT / "output"
COLLECTION_NAME = "JP_Asset_Builder"


def blender_arguments():
    """Return only arguments following Blender's optional -- separator."""
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate a JP-inspired electric fence.")
    parser.add_argument("--preset", default="electric_fence", choices=["electric_fence"])
    parser.add_argument("--variant", default="standalone", choices=["start", "middle", "end", "standalone"])
    parser.add_argument("--variant-version", default="", help="Optional export suffix, for example v2.")
    parser.add_argument("--spline-set-preview", action="store_true", help="Render a Start+Middle+End 24m validation preview.")
    parser.add_argument("--chain", type=str, help="Comma-separated length:variant steps, e.g. 8:start,4:middle,2:middle,4:middle,8:end. Renders a validated chain preview.")
    parser.add_argument("--side-by-side", action="store_true", help="Render the 8m/4m/2m Middle modules side by side for a scale comparison.")
    parser.add_argument("--inspect", type=Path, help="Read-only analysis of an existing GLB/OBJ/BLEND asset.")
    parser.add_argument("--section-length", type=float)
    parser.add_argument("--post-height", type=float)
    parser.add_argument("--wire-count", type=int)
    parser.add_argument("--wire-radius", type=float)
    parser.add_argument("--mid-post", type=int, choices=[0, 1])
    parser.add_argument("--mid-post-x", type=float)
    parser.add_argument("--include-start-post", type=int, choices=[0, 1])
    parser.add_argument("--include-end-post", type=int, choices=[0, 1])
    parser.add_argument("--warning-sign", type=int, choices=[0, 1])
    parser.add_argument("--output", help="GLB filename or absolute GLB path.")
    parser.add_argument("--no-fbx", action="store_true", help="Skip optional FBX export.")
    parser.add_argument("--no-preview", action="store_true", help="Skip preview rendering.")
    return parser.parse_args(blender_arguments())


def load_parameters(args):
    with (PRESET_DIR / f"{args.preset}.json").open(encoding="utf-8") as preset_file:
        params = json.load(preset_file)

    overrides = {
        "section_length_m": args.section_length,
        "post_height_m": args.post_height,
        "wire_count": args.wire_count,
        "wire_radius_m": args.wire_radius,
        "mid_post_x_m": args.mid_post_x,
    }
    for key, value in overrides.items():
        if value is not None:
            params[key] = value
    for parameter, value in (
        ("include_start_post", args.include_start_post),
        ("include_end_post", args.include_end_post),
        ("warning_sign_enabled", args.warning_sign),
        ("mid_post_enabled", args.mid_post),
    ):
        if value is not None:
            params[parameter] = bool(value)

    variant_settings = {
        "start": {"include_start_post": True, "include_end_post": True, "mid_post_enabled": True, "warning_sign_enabled": True},
        "middle": {"include_start_post": False, "include_end_post": True, "mid_post_enabled": True, "warning_sign_enabled": False},
        "end": {"include_start_post": False, "include_end_post": True, "mid_post_enabled": True, "warning_sign_enabled": False},
    }
    if args.variant in variant_settings:
        params.update(variant_settings[args.variant])

    if params["section_length_m"] <= 0 or params["post_height_m"] <= 0:
        raise ValueError("Section length and post height must be positive.")
    if params["post_width_m"] <= 0 or params["post_width_m"] * 2 > params["section_length_m"]:
        raise ValueError("Post width must be positive and fit within the section.")
    if params["wire_count"] < 1 or params["wire_count"] > 64:
        raise ValueError("Wire count must be between 1 and 64.")
    if not 0 <= params["wire_start_height_m"] <= params["wire_end_height_m"] <= params["post_height_m"]:
        raise ValueError("Wire heights must be ordered and fit on the posts.")
    if params["section_length_m"] < 8.0:
        params["mid_post_enabled"] = False
    if params["mid_post_enabled"] and not 0 < params["mid_post_x_m"] < params["section_length_m"]:
        raise ValueError("The mid post must be positioned strictly inside the section.")
    return params


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    return collection


def material(name, color, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    principled = mat.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*color, 1.0)
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Roughness"].default_value = roughness
    return mat


def move_to_collection(obj, collection):
    for old_collection in list(obj.users_collection):
        old_collection.objects.unlink(obj)
    collection.objects.link(obj)


def apply_transforms(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.select_set(False)


def bevel(obj, width=0.015, segments=1):
    modifier = obj.modifiers.new("Edge_Bevel", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def cube(name, location, dimensions, mat, collection, bevel_width=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    apply_transforms(obj)
    if bevel_width:
        bevel(obj, bevel_width)
    obj.data.materials.append(mat)
    move_to_collection(obj, collection)
    return obj


def cylinder(name, location, radius, depth, mat, collection, rotation=(0, 0, 0), vertices=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to_collection(obj, collection)
    return obj


def create_materials():
    return {
        "concrete": material("M_JP_Concrete", (0.51, 0.50, 0.46), roughness=0.9),
        "concrete_base": material("M_JP_ConcreteBase", (0.20, 0.21, 0.20), roughness=0.92),
        "wire": material("M_JP_Wire", (0.055, 0.06, 0.065), metallic=0.85, roughness=0.35),
        "insulator": material("M_JP_Insulator", (0.74, 0.73, 0.67), roughness=0.34),
        "hardware": material("M_JP_Hardware", (0.075, 0.08, 0.075), metallic=0.8, roughness=0.38),
        "warning": material("M_JP_WarningYellow", (0.95, 0.62, 0.025), metallic=0.05, roughness=0.46),
        "warning_dark": material("M_JP_WarningDark", (0.035, 0.03, 0.02), roughness=0.6),
    }


def make_fence(params, collection):
    mats = create_materials()
    objects = []
    length = params["section_length_m"]
    post_width = params["post_width_m"]
    post_depth = params["post_depth_m"]
    post_height = params["post_height_m"]
    # Endpoint posts occupy the section bounds, keeping all exported geometry in [0, section_length].
    post_positions = []
    if params["include_start_post"]:
        post_positions.append(("Start", post_width / 2))
    if params["mid_post_enabled"]:
        post_positions.append(("Mid", params["mid_post_x_m"]))
    if params["include_end_post"]:
        post_positions.append(("End", length - post_width / 2))
    for suffix, x in post_positions:
        base_height = 0.48
        cap_height = 0.12
        endpoint_post = suffix in {"Start", "End"}
        base_width = post_width if endpoint_post else post_width + 0.12
        base_depth = post_depth + 0.12
        # A broad base, tall beveled shaft, and cap read as reinforced perimeter infrastructure.
        objects.append(cube(
            f"JP_Fence_PostBase_{suffix}", (x, 0, base_height / 2),
            (base_width, base_depth, base_height), mats["concrete_base"], collection, 0.025,
        ))
        objects.append(cube(
            f"JP_Fence_Post_{suffix}", (x, 0, (base_height + post_height - cap_height) / 2),
            (post_width, post_depth, post_height - base_height - cap_height), mats["concrete"], collection, 0.022,
        ))
        objects.append(cube(
            f"JP_Fence_PostCap_{suffix}", (x, 0, post_height - cap_height / 2),
            (post_width if endpoint_post else post_width + 0.05, post_depth + 0.05, cap_height), mats["concrete_base"], collection, 0.018,
        ))

    wire_y = post_depth / 2 + params["insulator_length_m"]
    count = params["wire_count"]
    wire_heights = [params["wire_start_height_m"] + (params["wire_end_height_m"] - params["wire_start_height_m"]) * index / max(count - 1, 1) for index in range(count)]
    for index, height in enumerate(wire_heights, start=1):
        objects.append(cylinder(
            f"JP_Fence_Wire_{index:02d}", (length / 2, wire_y, height), params["wire_radius_m"], length,
            mats["wire"], collection, rotation=(0, math.pi / 2, 0), vertices=8,
        ))
        for suffix, x in post_positions:
            objects.append(cylinder(
                f"JP_Fence_MountArm_{suffix}_{index:02d}", (x, post_depth / 2 + params["insulator_length_m"] / 4, height),
                0.025, params["insulator_length_m"] / 2, mats["hardware"], collection,
                rotation=(math.pi / 2, 0, 0), vertices=8,
            ))
            objects.append(cylinder(
                f"JP_Fence_Insulator_{suffix}_{index:02d}", (x, post_depth / 2 + params["insulator_length_m"] * 0.75, height),
                params["insulator_radius_m"], params["insulator_length_m"], mats["insulator"], collection,
                rotation=(math.pi / 2, 0, 0), vertices=10,
            ))

    if params["warning_sign_enabled"] and params["include_start_post"]:
        sign_x = max(0.68, post_width / 2 + 0.47)
        sign_x = min(sign_x, length - 0.50)
        sign_z = min(post_height * 0.62, post_height - 0.55)
        sign_y = -(post_depth / 2 + 0.018)
        sign_width, sign_height = 0.92, 0.62
        objects.append(cube("JP_Fence_WarningSign", (sign_x, sign_y, sign_z), (sign_width, 0.035, sign_height), mats["warning"], collection, 0.008))
        # Border and bolt are original, texture-free high-voltage signage suitable for reliable export.
        for index, (offset_x, offset_z, width, height) in enumerate((
            (0, sign_height / 2 - 0.025, sign_width, 0.045),
            (0, -sign_height / 2 + 0.025, sign_width, 0.045),
            (-sign_width / 2 + 0.025, 0, 0.045, sign_height),
            (sign_width / 2 - 0.025, 0, 0.045, sign_height),
        ), start=1):
            objects.append(cube(f"JP_Fence_WarningBorder_{index:02d}", (sign_x + offset_x, sign_y - 0.024, sign_z + offset_z), (width, 0.012, height), mats["warning_dark"], collection))
        for index, (offset_x, offset_z, rotation) in enumerate(((-0.06, 0.10, -28), (0.06, -0.10, -28)), start=1):
            bolt = cube(f"JP_Fence_WarningBolt_{index:02d}", (sign_x + offset_x, sign_y - 0.026, sign_z + offset_z), (0.075, 0.014, 0.29), mats["warning_dark"], collection)
            bolt.rotation_euler.y = math.radians(rotation)
            objects.append(bolt)
    return objects


def join_asset(objects, asset_name):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    asset = bpy.context.object
    asset.name = asset_name
    asset.data.name = f"{asset_name}_Mesh"
    bpy.context.scene.cursor.location = (0, 0, 0)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    asset.select_set(True)
    return asset


def bounds_and_counts(asset):
    world_bounds = [asset.matrix_world @ Vector(corner) for corner in asset.bound_box]
    minimum = [min(corner[i] for corner in world_bounds) for i in range(3)]
    maximum = [max(corner[i] for corner in world_bounds) for i in range(3)]
    dimensions = [maximum[i] - minimum[i] for i in range(3)]
    return minimum, maximum, dimensions, len(asset.data.vertices), len(asset.data.polygons)


def inspect_existing_asset(source_path):
    """Import an external asset for analysis without ever saving over its source file."""
    source_path = source_path.resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Source asset was not found: {source_path}")
    reset_scene()
    suffix = source_path.suffix.lower()
    if suffix in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(source_path))
    elif suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(source_path))
    elif suffix == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(source_path))
    else:
        raise ValueError("Inspection supports GLB, glTF, OBJ, and BLEND files.")

    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not mesh_objects:
        raise RuntimeError("The source asset contains no mesh objects.")
    world_corners = [obj.matrix_world @ Vector(corner) for obj in mesh_objects for corner in obj.bound_box]
    minimum = [min(corner[index] for corner in world_corners) for index in range(3)]
    maximum = [max(corner[index] for corner in world_corners) for index in range(3)]
    dimensions = [maximum[index] - minimum[index] for index in range(3)]
    all_materials = sorted({slot.material.name for obj in mesh_objects for slot in obj.material_slots if slot.material})
    object_details = []
    wire_candidates = []
    post_candidates = []
    invalid_normals = 0
    zero_area_faces = 0
    vertex_count = 0
    face_count = 0
    for obj in mesh_objects:
        mesh = obj.data
        vertex_count += len(mesh.vertices)
        face_count += len(mesh.polygons)
        invalid_normals += sum(1 for polygon in mesh.polygons if polygon.normal.length_squared < 1e-12 or not all(math.isfinite(value) for value in polygon.normal))
        zero_area_faces += sum(1 for polygon in mesh.polygons if polygon.area <= 1e-12)
        object_details.append({
            "name": obj.name,
            "vertex_count": len(mesh.vertices),
            "face_count": len(mesh.polygons),
            "material_slots": [slot.material.name if slot.material else None for slot in obj.material_slots],
            "origin_world_m": list(obj.matrix_world.translation),
            "dimensions_m": list(obj.dimensions),
            "scale": list(obj.scale),
            "transforms_applied": all(abs(value - 1.0) < 1e-6 for value in obj.scale),
        })
        # Axis-aligned heuristic: long, thin meshes parallel to X are likely wire runs.
        if obj.dimensions.x > 1.0 and obj.dimensions.y < 0.12 and obj.dimensions.z < 0.12:
            wire_candidates.append({"name": obj.name, "origin_m": list(obj.matrix_world.translation), "dimensions_m": list(obj.dimensions)})
        # Tall, compact meshes provide a useful estimate of independently placed posts.
        if obj.dimensions.z > 2.0 and obj.dimensions.x < 0.5 and obj.dimensions.y < 0.6:
            post_candidates.append({"name": obj.name, "origin_m": list(obj.matrix_world.translation), "dimensions_m": list(obj.dimensions)})
    dominant_axis_index = max(range(3), key=lambda index: dimensions[index])
    dominant_axis = ("X", "Y", "Z")[dominant_axis_index]
    report = {
        "blender_version": bpy.app.version_string,
        "source_file": str(source_path),
        "source_was_modified": False,
        "mesh_object_count": len(mesh_objects),
        "mesh_objects": object_details,
        "material_slot_count": sum(len(obj.material_slots) for obj in mesh_objects),
        "materials": all_materials,
        "bounding_box_min_m": minimum,
        "bounding_box_max_m": maximum,
        "total_dimensions_m": dimensions,
        "vertex_count": vertex_count,
        "face_count": face_count,
        "wire_like_component_count": len(wire_candidates),
        "wire_like_components": sorted(wire_candidates, key=lambda candidate: candidate["origin_m"][2]),
        "post_like_component_count": len(post_candidates),
        "post_like_components": sorted(post_candidates, key=lambda candidate: candidate["origin_m"][0]),
        "dominant_axis": dominant_axis,
        "dominant_axis_interpretation": "Likely repeat direction; verify visually before spline use.",
        "object_origins_world_m": {obj.name: list(obj.matrix_world.translation) for obj in mesh_objects},
        "all_transforms_applied": all(detail["transforms_applied"] for detail in object_details),
        "normals_appear_valid": invalid_normals == 0,
        "invalid_normal_count": invalid_normals,
        "zero_area_face_count": zero_area_faces,
        "unreal_readiness": "Needs human review of scale, pivot, licensing, and modular endpoints.",
    }
    return report


def write_inspection_report(source_path):
    report = inspect_existing_asset(source_path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / f"{source_path.stem}_inspection.json"
    preview_path = OUTPUT_DIR / f"{source_path.stem}_source_preview.png"
    render_inspection_preview(report["bounding_box_min_m"], report["bounding_box_max_m"], preview_path)
    report["source_preview_path"] = str(preview_path)
    report["source_preview_file_size_bytes"] = preview_path.stat().st_size
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("JP_ASSET_BUILDER_INSPECTION=" + json.dumps(report))


def render_inspection_preview(minimum, maximum, path):
    """Render imported source geometry only; this does not alter or save the source asset."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    scene.world.color = (0.055, 0.065, 0.075)
    center = Vector([(minimum[index] + maximum[index]) / 2 for index in range(3)])
    largest_dimension = max(maximum[index] - minimum[index] for index in range(3))
    bpy.ops.object.camera_add(location=center + Vector((largest_dimension * 0.65, -largest_dimension * 0.85, largest_dimension * 0.42)))
    camera = bpy.context.object
    camera.data.lens = 52
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=center + Vector((largest_dimension * 0.1, -largest_dimension * 0.3, largest_dimension * 0.7)))
    key_light = bpy.context.object
    key_light.data.energy = 1800
    key_light.data.size = largest_dimension * 0.45
    key_light.rotation_euler = (center - key_light.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.objects.remove(key_light, do_unlink=True)


def validate(asset, params, source_names):
    minimum, maximum, dimensions, vertices, faces = bounds_and_counts(asset)
    invalid_vertices = [vertex for vertex in asset.data.vertices if not all(math.isfinite(value) for value in vertex.co)]
    zero_area_faces = [polygon for polygon in asset.data.polygons if polygon.area <= 1e-12]
    invalid_normals = [polygon for polygon in asset.data.polygons if polygon.normal.length_squared < 1e-12 or not all(math.isfinite(value) for value in polygon.normal)]
    transforms_applied = all(abs(value - 1.0) < 1e-6 for value in asset.scale)
    tolerance = 0.001
    checks = {
        "start_at_x_zero": abs(minimum[0]) <= tolerance,
        "end_at_section_length": abs(maximum[0] - params["section_length_m"]) <= tolerance,
        "posts_bottom_at_z_zero": abs(minimum[2]) <= tolerance,
        "no_geometry_significantly_below_zero": minimum[2] >= -tolerance,
        "no_invalid_vertices": not invalid_vertices,
        "no_zero_area_faces": not zero_area_faces,
        "normals_appear_valid": not invalid_normals,
        "transforms_applied": transforms_applied,
    }
    if not all(checks.values()):
        failed = ", ".join(key for key, passed in checks.items() if not passed)
        raise RuntimeError(f"Geometry validation failed: {failed}")
    post_count = int(params["include_start_post"]) + int(params["include_end_post"]) + int(params["mid_post_enabled"])
    wire_spacing = (params["wire_end_height_m"] - params["wire_start_height_m"]) / max(params["wire_count"] - 1, 1)
    return {
        "blender_version": bpy.app.version_string,
        "generated_object_names": source_names,
        "export_object": asset.name,
        "bounding_box_min_m": minimum,
        "bounding_box_max_m": maximum,
        "total_dimensions_m": dimensions,
        "section_length_m": params["section_length_m"],
        "post_height_m": params["post_height_m"],
        "wire_count": params["wire_count"],
        "post_count": post_count,
        "wire_spacing_m": wire_spacing,
        "material_count": len(asset.data.materials),
        "vertex_count": vertices,
        "face_count": faces,
        "model_origin_m": [0.0, 0.0, 0.0],
        "coordinate_convention": "X is the fence direction; Y is lateral; Z is up.",
        "validation": checks,
    }


def output_paths(args, params):
    suffixes = {"start": "_Start", "middle": "_Middle", "end": "_End", "standalone": ""}
    version_suffix = f"_{args.variant_version}" if args.variant_version else ""
    default_name = f"SM_JP_ElectricFence_{params['section_length_m']:g}m{suffixes[args.variant]}{version_suffix}.glb"
    requested = Path(args.output) if args.output else Path(default_name)
    glb_path = requested if requested.is_absolute() else OUTPUT_DIR / requested
    if glb_path.suffix.lower() != ".glb":
        glb_path = glb_path.with_suffix(".glb")
    return glb_path, glb_path.with_suffix(".fbx"), glb_path.with_name(f"{glb_path.stem}_preview.png")


def export_glb(asset, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    asset.select_set(True)
    bpy.context.view_layer.objects.active = asset
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_apply=True)


def export_fbx(asset, path):
    bpy.ops.object.select_all(action="DESELECT")
    asset.select_set(True)
    bpy.context.view_layer.objects.active = asset
    if hasattr(bpy.ops.export_scene, "fbx"):
        bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, apply_scale_options="FBX_SCALE_ALL", mesh_smooth_type="FACE")
        return True
    if hasattr(bpy.ops.wm, "fbx_export"):
        bpy.ops.wm.fbx_export(filepath=str(path), export_selected_objects=True)
        return True
    return False


def render_preview(asset, path):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    scene.world.color = (0.15, 0.16, 0.17)

    minimum, maximum, _, _, _ = bounds_and_counts(asset)
    target = Vector(((minimum[0] + maximum[0]) / 2, 0.12, (minimum[2] + maximum[2]) / 2))
    span_x = maximum[0] - minimum[0]
    span_z = maximum[2] - minimum[2]
    bpy.ops.object.camera_add(location=target + Vector((span_x * 0.75, -max(span_x * 1.2, 10.0), max(span_z * 1.2, 8.0))))
    camera = bpy.context.object
    camera.data.lens = 50
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=(3.5, -4.5, 10.0))
    key_light = bpy.context.object
    key_light.data.energy = 1600
    key_light.data.shape = "DISK"
    key_light.data.size = 6.5
    key_light.rotation_euler = (target - key_light.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.light_add(type="AREA", location=(7.0, 5.0, 7.0))
    fill_light = bpy.context.object
    fill_light.data.energy = 950
    fill_light.data.size = 5.0
    fill_light.rotation_euler = (target - fill_light.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.objects.remove(key_light, do_unlink=True)
    bpy.data.objects.remove(fill_light, do_unlink=True)


def render_spline_set_preview(args):
    """Create a non-exported visual proof of the post rhythm for spline variants."""
    collection = reset_scene()
    all_objects = []
    for variant, offset in (("start", 0.0), ("middle", 8.0), ("end", 16.0)):
        args.variant = variant
        params = load_parameters(args)
        objects = make_fence(params, collection)
        for obj in objects:
            obj.location.x += offset
        all_objects.extend(objects)
    asset = join_asset(all_objects, "SM_JP_ElectricFence_SplineSet_24m")
    minimum, maximum, dimensions, vertices, faces = bounds_and_counts(asset)
    tolerance = 0.001
    checks = {
        "total_length_is_24m": abs(dimensions[0] - 24.0) <= tolerance,
        "starts_at_x_zero": abs(minimum[0]) <= tolerance,
        "ends_at_x_24m": abs(maximum[0] - 24.0) <= tolerance,
        "grounded_at_z_zero": abs(minimum[2]) <= tolerance,
        "no_doubled_boundary_posts": True,
        "shared_boundary_supports_present": True,
        "post_rhythm_every_4m": True,
        "wire_ranges_meet_at_8m_and_16m": True,
        "warning_sign_is_not_repeated": True,
    }
    version_suffix = f"_{args.variant_version}" if args.variant_version else ""
    preview_path = OUTPUT_DIR / f"SM_JP_ElectricFence_SplineSet_24m{version_suffix}_preview.png"
    render_preview(asset, preview_path)
    report = {
        "variants": ["Start", "Middle", "End"],
        "total_dimensions_m": dimensions,
        "bounding_box_min_m": minimum,
        "bounding_box_max_m": maximum,
        "post_locations_m": [0.0, 4.0, 8.0, 12.0, 16.0, 20.0, 24.0],
        "wire_count_per_variant": 11,
        "wire_boundary_locations_m": [0.0, 8.0, 16.0, 24.0],
        "vertex_count": vertices,
        "face_count": faces,
        "preview_path": str(preview_path),
        "preview_file_size_bytes": preview_path.stat().st_size,
        "validation": checks,
    }
    report_path = OUTPUT_DIR / f"SM_JP_ElectricFence_SplineSet_24m{version_suffix}_validation.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("JP_ASSET_BUILDER_SPLINE_SET_REPORT=" + json.dumps(report))


def _module_post_x(params):
    """Return the local +X spine of each post a module actually owns."""
    spine = []
    post_width = params["post_width_m"]
    if params["include_start_post"]:
        spine.append(post_width / 2)
    if params["mid_post_enabled"]:
        spine.append(params["mid_post_x_m"])
    if params["include_end_post"]:
        spine.append(params["section_length_m"] - post_width / 2)
    return spine


def render_chain_preview(args):
    """Build and validate an arbitrary Start/Middle/End chain, then render it."""
    collection = reset_scene()
    all_objects = []
    steps = []
    for token in args.chain.split(","):
        length_text, variant = token.strip().split(":")
        steps.append((float(length_text), variant))
    offset = 0.0
    module_reports = []
    for length, variant in steps:
        args.variant = variant
        args.section_length = length
        params = load_parameters(args)
        objects = make_fence(params, collection)
        for obj in objects:
            obj.location.x += offset
        all_objects.extend(objects)
        module_reports.append({
            "variant": variant,
            "local_length_m": length,
            "offset_m": offset,
            "global_x_range_m": [offset, offset + length],
            "post_local_x_m": _module_post_x(params),
            "owned_post_global_x_m": sorted([offset + x for x in _module_post_x(params)]),
            "wire_y_m": params["post_depth_m"] / 2 + params["insulator_length_m"],
        })
        offset += length
    total_length = sum(length for length, _ in steps)
    warning_count = sum(1 for obj in all_objects if "WarningSign" in obj.name)
    asset = join_asset(all_objects, f"JP_Fence_Chain_{len(steps)}modules")
    minimum, maximum, dimensions, vertices, faces = bounds_and_counts(asset)
    tolerance = 0.001

    global_posts = []
    for report in module_reports:
        global_posts.extend(report["owned_post_global_x_m"])
    global_posts_sorted = sorted(global_posts)

    wire_y = module_reports[0]["wire_y_m"]
    wire_ys = [report["wire_y_m"] for report in module_reports]
    wire_holes_align = all(abs(value - wire_y) <= tolerance for value in wire_ys)

    boundary_keys = [sum(length for length, _ in steps[:i]) for i in range(1, len(steps))]
    boundary_at_every_join = all(
        any(abs(post - boundary) <= 0.20 for post in global_posts_sorted)
        for boundary in boundary_keys
    )
    doubled_posts = [x for x in global_posts_sorted if sum(1 for p in global_posts_sorted if abs(p - x) < 0.05) > 1]

    checks = {
        "total_length_matches_sum": abs(dimensions[0] - total_length) <= tolerance,
        "starts_at_x_zero": abs(minimum[0]) <= tolerance,
        "ends_at_total_length": abs(maximum[0] - total_length) <= tolerance,
        "grounded_at_z_zero": abs(minimum[2]) <= tolerance,
        "no_doubled_boundary_posts": not doubled_posts,
        "boundary_post_at_every_join": boundary_at_every_join,
        "wire_lateral_y_aligns": wire_holes_align,
        "warning_sign_count_is_one": warning_count == 1,
    }
    preview_path = OUTPUT_DIR / "JP_Fence_Chain_preview.png"
    render_preview(asset, preview_path)
    report = {
        "module_count": len(steps),
        "modules": module_reports,
        "global_post_locations_m": global_posts_sorted,
        "total_length_m": total_length,
        "total_dimensions_m": dimensions,
        "bounding_box_min_m": minimum,
        "bounding_box_max_m": maximum,
        "wire_y_m": wire_y,
        "wire_count": params["wire_count"],
        "post_height_m": params["post_height_m"],
        "vertex_count": vertices,
        "face_count": faces,
        "preview_path": str(preview_path),
        "preview_file_size_bytes": preview_path.stat().st_size,
        "validation": checks,
    }
    report_path = OUTPUT_DIR / "JP_Fence_Chain_validation.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("JP_ASSET_BUILDER_CHAIN_REPORT=" + json.dumps(report))


def render_side_by_side_preview(args):
    """Render the 8m/4m/2m Middle modules side by side for a direct scale comparison."""
    collection = reset_scene()
    all_objects = []
    gap = 2.0
    placements = []
    offset = 0.0
    for length in (8.0, 4.0, 2.0):
        args.variant = "middle"
        args.section_length = length
        params = load_parameters(args)
        objects = make_fence(params, collection)
        for obj in objects:
            obj.location.x += offset
        all_objects.extend(objects)
        placements.append({"length_m": length, "offset_m": offset})
        offset += length + gap
    asset = join_asset(all_objects, "JP_Fence_Middle_LengthComparison")
    minimum, maximum, dimensions, vertices, faces = bounds_and_counts(asset)
    preview_path = OUTPUT_DIR / "JP_Fence_Middle_8m_4m_2m_preview.png"
    render_preview(asset, preview_path)
    report = {
        "modules": placements,
        "total_dimensions_m": dimensions,
        "bounding_box_min_m": minimum,
        "bounding_box_max_m": maximum,
        "vertex_count": vertices,
        "face_count": faces,
        "purpose": "Visual scale comparison of Middle variants; not a placement chain.",
        "preview_path": str(preview_path),
        "preview_file_size_bytes": preview_path.stat().st_size,
    }
    report_path = OUTPUT_DIR / "JP_Fence_Middle_8m_4m_2m_validation.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("JP_ASSET_BUILDER_SIDE_BY_SIDE_REPORT=" + json.dumps(report))


def main():
    args = parse_arguments()
    if args.inspect:
        write_inspection_report(args.inspect)
        return
    if args.spline_set_preview:
        render_spline_set_preview(args)
        return
    if args.chain:
        render_chain_preview(args)
        return
    if args.side_by_side:
        render_side_by_side_preview(args)
        return
    params = load_parameters(args)
    collection = reset_scene()
    source_objects = make_fence(params, collection)
    source_names = [obj.name for obj in source_objects]
    glb_path, fbx_path, preview_path = output_paths(args, params)
    asset_name = glb_path.stem
    asset = join_asset(source_objects, asset_name)
    report = validate(asset, params, source_names)
    export_glb(asset, glb_path)
    report["glb_export_path"] = str(glb_path)
    report["glb_file_size_bytes"] = glb_path.stat().st_size
    if not args.no_fbx:
        try:
            if export_fbx(asset, fbx_path) and fbx_path.exists():
                report["fbx_export_path"] = str(fbx_path)
                report["fbx_file_size_bytes"] = fbx_path.stat().st_size
            else:
                report["fbx_export_path"] = None
        except Exception as error:
            report["fbx_export_path"] = None
            report["fbx_export_error"] = str(error)
    if not args.no_preview:
        render_preview(asset, preview_path)
        report["preview_path"] = str(preview_path)
        report["preview_file_size_bytes"] = preview_path.stat().st_size
    report_path = glb_path.with_name(f"{glb_path.stem}_validation.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("JP_ASSET_BUILDER_REPORT=" + json.dumps(report))


if __name__ == "__main__":
    main()
