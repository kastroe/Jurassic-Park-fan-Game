import unreal

ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = ues.get_editor_world()

proxies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LandscapeProxy)
count = 0
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    label = a.get_actor_label()
    if label.startswith("JP93_"):
        count += 1
        loc = a.get_actor_location()
        unreal.log("JPVERIFY93 %s X=%.1f Y=%.1f Z=%.1f" % (label, loc.x, loc.y, loc.z))

unreal.log("JPVERIFY93_COUNT=%d LANDSCAPES=%d" % (count, len(proxies)))
unreal.SystemLibrary.execute_console_command(world, "MAP CHECKDEP NOCLEARLOG")
unreal.log("JPVERIFY93 SUCCESS")
unreal.SystemLibrary.quit_editor()
