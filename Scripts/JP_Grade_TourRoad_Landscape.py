import unreal


try:
    if not unreal.JPJurassicDreamLandscapeImportLibrary.grade_tour_road_landscape():
        raise RuntimeError("Tour Road Landscape grading failed")
    world = unreal.EditorLevelLibrary.get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "MAP CHECKDEP NOCLEARLOG")
    unreal.log("JPGRADING PYTHON_SUCCESS")
finally:
    unreal.SystemLibrary.quit_editor()
