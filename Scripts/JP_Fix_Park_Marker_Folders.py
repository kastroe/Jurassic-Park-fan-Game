import unreal

ok = unreal.JPJurassicDreamLandscapeImportLibrary.assign_temp_marker_folders()
if not ok:
    raise RuntimeError("marker folder assignment failed")
unreal.log("JPARKFIX SUCCESS")
unreal.SystemLibrary.quit_editor()
