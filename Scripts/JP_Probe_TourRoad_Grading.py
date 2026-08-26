import unreal


try:
    if not unreal.JPJurassicDreamLandscapeImportLibrary.probe_tour_road_grading():
        raise RuntimeError("Tour Road grading probe failed")
finally:
    unreal.SystemLibrary.quit_editor()
