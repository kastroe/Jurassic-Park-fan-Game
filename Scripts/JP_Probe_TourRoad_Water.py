import unreal


try:
    if not unreal.JPJurassicDreamLandscapeImportLibrary.probe_tour_road_water_crossing():
        raise RuntimeError("Tour Road water probe failed")
finally:
    unreal.SystemLibrary.quit_editor()
