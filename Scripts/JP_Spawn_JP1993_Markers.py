import unreal

CSV = ("Visitor Center,165000,215000,400;"
       "Main Gate,185000,193000,400;"
       "Heliport,205000,95000,400;"
       "Port,370000,232000,400;"
       "T-Rex Paddock,132000,298000,400;"
       "Dilophosaurus,162000,142000,400;"
       "Brachiosaurus,262000,224000,400;"
       "Triceratops,272000,156000,400;"
       "Gallimimus,237000,204000,400;"
       "Velociraptor,140000,315000,400")

ok = unreal.JPJurassicDreamLandscapeImportLibrary.spawn_jp1993_markers(CSV)
if not ok:
    raise RuntimeError("JP1993 marker spawn failed")
unreal.log("JP1993 SPAWN SUCCESS")
unreal.SystemLibrary.quit_editor()
