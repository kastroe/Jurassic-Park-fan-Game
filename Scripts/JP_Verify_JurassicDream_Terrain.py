import traceback

import unreal


EXPECTED_MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _run():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = ues.get_editor_world() if ues else None
    if world is None:
        raise RuntimeError("verify refused: no editor world is loaded.")

    package_name = world.get_outermost().get_name()
    if package_name != EXPECTED_MAP:
        raise RuntimeError("verify refused: active package is %s, expected %s" % (package_name, EXPECTED_MAP))

    proxies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LandscapeProxy)
    if len(proxies) != 1:
        raise RuntimeError("Expected exactly 1 LandscapeProxy, found %d." % len(proxies))

    proxy = proxies[0]
    label = proxy.get_actor_label()
    raw_name = proxy.get_name()
    location = proxy.get_actor_location()
    scale = proxy.get_actor_scale3d()
    heightfield_components = proxy.get_components_by_class(unreal.LandscapeComponent)
    collision_components = proxy.get_components_by_class(unreal.LandscapeHeightfieldCollisionComponent)

    unreal.log("JPVERIFY_ACTOR_LABEL=%s" % label)
    unreal.log("JPVERIFY_ACTOR_NAME=%s" % raw_name)
    unreal.log("JPVERIFY_COMPONENT_COUNT=%d" % len(heightfield_components))
    unreal.log("JPVERIFY_COLLISION_COMPONENT_COUNT=%d" % len(collision_components))
    unreal.log(
        "JPVERIFY_SCALE X=%.7f Y=%.7f Z=%.7f"
        % (scale.x, scale.y, scale.z)
    )
    unreal.log(
        "JPVERIFY_LOCATION X=%.4f Y=%.4f Z=%.4f"
        % (location.x, location.y, location.z)
    )


    unreal.SystemLibrary.execute_console_command(world, "MAP CHECKDEP NOCLEARLOG")
    unreal.log("JPVERIFY_SUCCESS")


try:
    _run()
except Exception:
    unreal.log_error("JPVERIFY_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
