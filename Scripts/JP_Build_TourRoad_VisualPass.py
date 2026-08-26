import unreal


MATERIAL_FOLDER = "/Game/Temp/TourRoad_Final"


def create_material(name, color, metallic, roughness, specular):
    path = f"{MATERIAL_FOLDER}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.EditorAssetLibrary.load_asset(path)

    unreal.EditorAssetLibrary.make_directory(MATERIAL_FOLDER)
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, MATERIAL_FOLDER, unreal.Material, unreal.MaterialFactoryNew()
    )
    if material is None:
        raise RuntimeError(f"Could not create {path}")

    color_node = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionConstant3Vector, -400, 0
    )
    color_node.constant = unreal.LinearColor(*color, 1.0)
    unreal.MaterialEditingLibrary.connect_material_property(
        color_node, "", unreal.MaterialProperty.MP_BASE_COLOR
    )
    for y, value, material_property in (
        (120, metallic, unreal.MaterialProperty.MP_METALLIC),
        (240, roughness, unreal.MaterialProperty.MP_ROUGHNESS),
        (360, specular, unreal.MaterialProperty.MP_SPECULAR),
    ):
        node = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionConstant, -400, y
        )
        node.r = value
        unreal.MaterialEditingLibrary.connect_material_property(node, "", material_property)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)
    return material


try:
    create_material("M_TourRoad_Asphalt", (0.025, 0.028, 0.032), 0.0, 0.88, 0.22)
    create_material("M_TourGuideTrack_Metal", (0.24, 0.26, 0.28), 1.0, 0.28, 0.5)
    if not unreal.JPJurassicDreamLandscapeImportLibrary.build_tour_road_visual_pass():
        raise RuntimeError("Tour Road visual pass failed")
    world = unreal.EditorLevelLibrary.get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "MAP CHECKDEP NOCLEARLOG")
    unreal.log("JPTOUR_FINAL PYTHON_SUCCESS")
finally:
    unreal.SystemLibrary.quit_editor()
