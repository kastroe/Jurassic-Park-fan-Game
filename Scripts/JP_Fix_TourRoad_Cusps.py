import unreal
ok = unreal.JPJurassicDreamLandscapeImportLibrary.fix_tour_road_cusps()
if not ok:
    raise RuntimeError("Fix cusps failed")
unreal.log("JPCUSP FIX SUCCESS")
unreal.SystemLibrary.quit_editor()
