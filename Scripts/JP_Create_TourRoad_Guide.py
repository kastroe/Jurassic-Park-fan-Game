import unreal
ok = unreal.JPJurassicDreamLandscapeImportLibrary.create_tour_road_guide()
if not ok:
    raise RuntimeError("TourRoad guide failed")
unreal.log("JPTOUR SUCCESS")
unreal.SystemLibrary.quit_editor()
