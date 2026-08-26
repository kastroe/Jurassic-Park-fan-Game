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
        raise RuntimeError("Native terrain import refused: no editor world is loaded.")

    package_name = world.get_outermost().get_name()
    if package_name != EXPECTED_MAP:
        raise RuntimeError(
            "Native terrain import refused: active package is %s, expected %s"
            % (package_name, EXPECTED_MAP)
        )

    if not unreal.JPJurassicDreamLandscapeImportLibrary.import_jurassic_dream_terrain():
        raise RuntimeError("Native Jurassic Dream terrain import returned failure.")

    proxies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LandscapeProxy)
    if len(proxies) != 1:
        raise RuntimeError("Expected exactly 1 LandscapeProxy, found %d." % len(proxies))

    proxy = proxies[0]
    label = proxy.get_actor_label()
    location = proxy.get_actor_location()
    scale = proxy.get_actor_scale3d()
    component_count = len(proxy.landscape_components)

    unreal.log("JPIMPORT_ACTOR_NAME=%s" % label)
    unreal.log("JPIMPORT_COMPONENT_COUNT=%d" % component_count)
    unreal.log(
        "JPIMPORT_TRANSFORM X=%.7f Y=%.7f Z=%.7f ActorZ=%.4f"
        % (scale.x, scale.y, scale.z, location.z)
    )

    unreal.SystemLibrary.execute_console_command(world, "MAP CHECKDEP NOCLEARLOG")
    unreal.log("JPIMPORT_SUCCESS")


try:
    _run()
except Exception:
    unreal.log_error("JPIMPORT_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
