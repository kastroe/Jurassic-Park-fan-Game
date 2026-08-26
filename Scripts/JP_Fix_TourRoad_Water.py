import unreal


try:
    if not unreal.JPJurassicDreamLandscapeImportLibrary.fix_tour_road_water_crossing():
        raise RuntimeError("Tour Road water repair failed")
    world = unreal.EditorLevelLibrary.get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "MAP CHECKDEP NOCLEARLOG")
    unreal.log("JPWATER_FIX PYTHON_SUCCESS")
finally:
    unreal.SystemLibrary.quit_editor()
