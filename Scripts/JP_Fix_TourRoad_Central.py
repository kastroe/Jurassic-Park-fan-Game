import unreal
ok = unreal.JPJurassicDreamLandscapeImportLibrary.fix_tour_road_guide_central_ridge()
if not ok:
    raise RuntimeError("TourRoad fix failed")
unreal.log("JPTOUR_FIX SUCCESS")
unreal.SystemLibrary.quit_editor()
