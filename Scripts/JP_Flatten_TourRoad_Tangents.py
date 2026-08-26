import unreal


try:
    ok = unreal.JPJurassicDreamLandscapeImportLibrary.flatten_tour_road_cusps_tangents()
    if not ok:
        raise RuntimeError("Flatten tangents failed")
    world = unreal.EditorLevelLibrary.get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "MAP CHECKDEP NOCLEARLOG")
    unreal.log("JPCUSP_TANGENT FIX SUCCESS")
finally:
    unreal.SystemLibrary.quit_editor()
