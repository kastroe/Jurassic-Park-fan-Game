import unreal


EXPECTED_MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"
EXPECTED_FOLDER = "JP1993_Layout/TourRoad_Final"


try:
    world = unreal.EditorLevelLibrary.get_editor_world()
    if world.get_outermost().get_name() != EXPECTED_MAP:
        raise RuntimeError(f"Unexpected map: {world.get_outermost().get_name()}")

    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    guides = [actor for actor in actors if actor.get_actor_label() == "TOUR_RoadGuide"]
    roads = [actor for actor in actors if actor.get_actor_label().startswith("TOUR_FinalRoad_")]
    tracks = [actor for actor in actors if actor.get_actor_label().startswith("TOUR_GuideTrack_")]
    ribbons = [actor for actor in actors if actor.get_actor_label().startswith("TOUR_Ribbon_")]
    markers = [actor for actor in actors if actor.get_actor_label().startswith("JP93_")]
    if len(guides) != 1:
        raise RuntimeError(f"Expected one guide, found {len(guides)}")

    spline = guides[0].get_component_by_class(unreal.SplineComponent)
    bad_folders = [
        actor.get_actor_label()
        for actor in roads + tracks
        if str(actor.get_folder_path()) != EXPECTED_FOLDER
    ]
    collision_states = set()
    bad_collision = []
    for actor in roads + tracks:
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        collision_state = component.get_collision_enabled()
        collision_states.add(str(collision_state))
        if "NO_COLLISION" not in str(collision_state).upper():
            bad_collision.append(actor.get_actor_label())
    visible_ribbons = []
    for actor in ribbons:
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if component and component.is_visible():
            visible_ribbons.append(actor.get_actor_label())

    unreal.log(f"JPTOUR_FINAL_COLLISION_STATES {sorted(collision_states)}")
    if bad_folders or bad_collision or visible_ribbons:
        raise RuntimeError(
            f"Visual verification failed: folders={len(bad_folders)} "
            f"collision={len(bad_collision)} visible_ribbons={len(visible_ribbons)}"
        )
    if len(roads) != 988 or len(tracks) != 988 or len(ribbons) != 741 or len(markers) != 10:
        raise RuntimeError(
            f"Unexpected counts: roads={len(roads)} tracks={len(tracks)} "
            f"ribbons={len(ribbons)} markers={len(markers)}"
        )
    if spline.get_number_of_spline_points() != 14:
        raise RuntimeError(f"Unexpected spline point count: {spline.get_number_of_spline_points()}")

    unreal.log(
        f"JPTOUR_FINAL_POSTSAVE MAP={world.get_outermost().get_name()} "
        f"POINTS={spline.get_number_of_spline_points()} LENGTH={spline.get_spline_length():.1f} "
        f"ROAD_SEGMENTS={len(roads)} TRACK_SEGMENTS={len(tracks)} "
        f"RIBBONS_HIDDEN={len(ribbons)} JP93={len(markers)} COLLISION_ISSUES=0 "
        f"COLLISION_STATES={sorted(collision_states)}"
    )
    unreal.SystemLibrary.execute_console_command(world, "MAP CHECKDEP NOCLEARLOG")
finally:
    unreal.SystemLibrary.quit_editor()
