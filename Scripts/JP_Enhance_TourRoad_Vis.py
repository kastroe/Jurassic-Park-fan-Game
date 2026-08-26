import unreal
ok = unreal.JPJurassicDreamLandscapeImportLibrary.enhance_tour_road_visualization()
if not ok:
    raise RuntimeError("Enhance visualization failed")
unreal.log("JPTOUR_VIS SUCCESS")
unreal.SystemLibrary.quit_editor()
