import unreal

CSV = ("Raptor F,140000,315000;"
       "Raptor G,160000,310000;"
       "Raptor H,180000,305000;"
       "Raptor I,200000,295000;"
       "Raptor J,170000,290000")

ok = unreal.JPJurassicDreamLandscapeImportLibrary.probe_jp1993_heights(CSV)
if not ok:
    raise RuntimeError("probe failed")
unreal.log("JP1993 PROBE4 SUCCESS")
unreal.SystemLibrary.quit_editor()
