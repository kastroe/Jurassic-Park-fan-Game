import unreal


try:
    world = unreal.EditorLevelLibrary.get_editor_world()
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    guides = [actor for actor in actors if actor.get_actor_label() == "TOUR_RoadGuide"]
    ribbons = [actor for actor in actors if actor.get_actor_label().startswith("TOUR_Ribbon_")]
    jp93_markers = [actor for actor in actors if actor.get_actor_label().startswith("JP93_")]
    temp_markers = [
        actor
        for actor in actors
        if str(actor.get_folder_path()).startswith("TEMP_Markers")
        and not actor.get_actor_label().startswith("TEMP_Label_")
    ]
    if len(guides) != 1:
        raise RuntimeError(f"Expected one TOUR_RoadGuide, found {len(guides)}")
    spline = guides[0].get_component_by_class(unreal.SplineComponent)
    if spline.get_number_of_spline_points() != 14:
        raise RuntimeError(
            f"Expected 14 spline points, found {spline.get_number_of_spline_points()}"
        )
    unreal.log(
        f"JPTAN_POSTSAVE MAP={world.get_outermost().get_name()} "
        f"POINTS={spline.get_number_of_spline_points()} LENGTH={spline.get_spline_length():.1f} "
        f"RIBBONS={len(ribbons)} JP93={len(jp93_markers)} TEMP_MARKERS={len(temp_markers)}"
    )
    unreal.SystemLibrary.execute_console_command(world, "MAP CHECKDEP NOCLEARLOG")
finally:
    unreal.SystemLibrary.quit_editor()
