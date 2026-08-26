import unreal

ok = unreal.JPJurassicDreamLandscapeImportLibrary.snap_temp_markers_to_landscape()
if not ok:
    raise RuntimeError("marker snap failed")
unreal.log("JPSNAP SUCCESS")
unreal.SystemLibrary.quit_editor()
