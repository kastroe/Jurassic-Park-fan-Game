import traceback

import unreal


EXPECTED_MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"
MATERIAL_PATH = "/Game/Temp/M_TEMP_WaterLevel50m"
PLANE_HALF_SIZE_CM = 225000.0
LANDSCAPE_CENTER = unreal.Vector(204800.0, 204800.0, 0.0)
WORLD_WATER_Z = 5000.0


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _log(msg):
    unreal.log("JPVIS %s" % msg)


def _make_or_load_material():
    try:
        if unreal.EditorAssetLibrary.does_asset_exist(MATERIAL_PATH):
            return unreal.EditorAssetLibrary.load_asset(MATERIAL_PATH)

        unreal.EditorAssetLibrary.make_directory("/Game/Temp")
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mat = tools.create_asset(
            "M_TEMP_WaterLevel50m", "/Game/Temp", unreal.Material, unreal.MaterialFactoryNew())
        if mat is None:
            raise RuntimeError("asset tool returned None")

        color_node = unreal.MaterialEditingLibrary.create_material_expression(
            mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
        color_node.constant = unreal.LinearColor(0.03, 0.20, 0.52, 1.0)
        unreal.MaterialEditingLibrary.connect_material_property(
            color_node, "", unreal.MaterialProperty.MP_BASE_COLOR)

        try:
            mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
            opac_node = unreal.MaterialEditingLibrary.create_material_expression(
                mat, unreal.MaterialExpressionConstant, -400, 220)
            opac_node.r = 0.35
            unreal.MaterialEditingLibrary.connect_material_property(
                opac_node, "", unreal.MaterialProperty.MP_OPACITY)
        except Exception as e:
            _log("opacity/blend skipped: %s" % e)

        unreal.MaterialEditingLibrary.recompile_material(mat)
        unreal.EditorAssetLibrary.save_loaded_asset(mat)
        return mat
    except Exception as e:
        _log("custom material failed (%s); falling back to WorldGridMaterial" % e)
        return unreal.EditorAssetLibrary.load_asset("/Engine/EngineMaterials/WorldGridMaterial")


def _run():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = ues.get_editor_world() if ues else None
    if world is None:
        raise RuntimeError("vis refused: no editor world is loaded.")

    package_name = world.get_outermost().get_name()
    if package_name != EXPECTED_MAP:
        raise RuntimeError("vis refused: active package is %s, expected %s" % (package_name, EXPECTED_MAP))

    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    existing = actor_sub.get_all_level_actors()
    for a in existing:
        label = a.get_actor_label()
        if label.startswith("TEMP_"):
            raise RuntimeError("vis refused: actor '%s' already exists." % label)

    landscapes = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LandscapeProxy)
    if len(landscapes) != 1:
        raise RuntimeError("vis refused: expected exactly 1 LandscapeProxy.")
    landscape = landscapes[0]
    pre_loc = landscape.get_actor_location()
    pre_scale = landscape.get_actor_scale3d()

    material = _make_or_load_material()
    _log("MATERIAL=%s" % MATERIAL_PATH)

    plane_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane")
    water = actor_sub.spawn_actor_from_object(
        plane_mesh,
        unreal.Vector(LANDSCAPE_CENTER.x, LANDSCAPE_CENTER.y, WORLD_WATER_Z),
        unreal.Rotator(0.0, 0.0, 0.0))
    water.set_actor_label("TEMP_WaterLevel_50m")
    water.set_actor_scale3d(unreal.Vector(
        PLANE_HALF_SIZE_CM * 2.0 / 100.0,
        PLANE_HALF_SIZE_CM * 2.0 / 100.0,
        1.0))
    mesh_comp = water.get_component_by_class(unreal.StaticMeshComponent)
    if mesh_comp is not None and material is not None:
        mesh_comp.set_material(0, material)

    sun = actor_sub.spawn_actor_from_class(
        unreal.DirectionalLight,
        unreal.Vector(LANDSCAPE_CENTER.x, LANDSCAPE_CENTER.y, 300000.0),
        unreal.Rotator(-55.0, 35.0, 0.0))
    sun.set_actor_label("TEMP_DirectionalLight")
    try:
        sun_comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
        if sun_comp is not None:
            sun_comp.set_editor_property("intensity", 5.0)
            sun_comp.set_editor_property("b_atmosphere_sun_light", True)
    except Exception as e:
        _log("sun intensity skipped: %s" % e)

    sky = actor_sub.spawn_actor_from_class(
        unreal.SkyLight,
        unreal.Vector(LANDSCAPE_CENTER.x, LANDSCAPE_CENTER.y, 250000.0),
        unreal.Rotator(0.0, 0.0, 0.0))
    sky.set_actor_label("TEMP_SkyLight")

    try:
        for a in (water, sun, sky):
            try:
                a.set_folder_path("TEMP_Visualization")
            except Exception:
                actor_sub.set_actor_folder_path(a, "TEMP_Visualization")
    except Exception as e:
        _log("folder path skipped: %s" % e)

    wloc = water.get_actor_location()
    sloc = sun.get_actor_location()
    kloc = sky.get_actor_location()
    _log("ACTOR_LABEL=TEMP_WaterLevel_50m LOC X=%.1f Y=%.1f Z=%.1f SCALE=%.1fx%.1f"
         % (wloc.x, wloc.y, wloc.z, water.get_actor_scale3d().x, water.get_actor_scale3d().y))
    _log("ACTOR_LABEL=TEMP_DirectionalLight LOC X=%.1f Y=%.1f Z=%.1f"
         % (sloc.x, sloc.y, sloc.z))
    _log("ACTOR_LABEL=TEMP_SkyLight LOC X=%.1f Y=%.1f Z=%.1f"
         % (kloc.x, kloc.y, kloc.z))

    post_loc = landscape.get_actor_location()
    post_scale = landscape.get_actor_scale3d()
    unchanged = (pre_loc == post_loc and pre_scale == post_scale)
    _log("LANDSCAPE_UNCHANGED=%s" % unchanged)
    if not unchanged:
        raise RuntimeError("landscape transform changed unexpectedly.")

    level_package = world.get_outermost()
    saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_package], False)
    if not saved:
        saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_package], True)
    _log("SAVED=%s" % saved)
    if not saved:
        raise RuntimeError("saving the target level failed.")

    unreal.SystemLibrary.execute_console_command(world, "MAP CHECKDEP NOCLEARLOG")
    _log("SUCCESS")


try:
    _run()
except Exception:
    unreal.log_error("JPVIS_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
