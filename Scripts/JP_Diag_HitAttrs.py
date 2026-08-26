import unreal


try:
    world = unreal.EditorLevelLibrary.get_editor_world()
    hit = unreal.SystemLibrary.line_trace_single_for_objects(
        world,
        unreal.Vector(204800.0, 204800.0, 500000.0),
        unreal.Vector(204800.0, 204800.0, -500000.0),
        [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1],
        False, [],
        unreal.DrawDebugTrace.NONE)
    unreal.log("JPHIT ATTRS: " + ",".join(a for a in dir(hit) if not a.startswith("_")))
finally:
    unreal.SystemLibrary.quit_editor()
