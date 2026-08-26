import json
import traceback

import unreal


EXPECTED_MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"
MARKER_JSON = r"C:\Users\KASTROE\Downloads\JurassicPark1993_FanGame_UE58\Intermediate\JPD_Markers.json"

CANON_LOC = (409600.0, 409600.0, 51200.78125)
CANON_SCALE = (100.392159, 100.392159, 200.003052)

CATEGORY_COLORS = {
    "Roads": (1.0, 0.5, 0.0),
    "Arrival": (0.2, 1.0, 1.0),
    "Vehicles": (1.0, 0.9, 0.1),
    "Fences": (0.95, 0.15, 0.15),
    "TrexPaddock": (1.0, 0.25, 1.0),
    "Gates": (0.25, 1.0, 0.35),
    "Bridge": (0.65, 0.85, 1.0),
}
CATEGORY_FOLDER = {
    "Roads": "TEMP_Markers/Roads",
    "Arrival": "TEMP_Markers/Arrival",
    "Vehicles": "TEMP_Markers/Vehicles",
    "Fences": "TEMP_Markers/Fences",
    "TrexPaddock": "TEMP_Markers/Fences/TrexPaddock",
    "Gates": "TEMP_Markers/Gates",
    "Bridge": "TEMP_Markers/Bridge",
}
LABELLED_CATS = {"Roads", "Arrival", "Vehicles", "Gates", "Bridge"}
SPHERE_SCALE = 4.0


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _log(msg):
    unreal.log("JPARK %s" % msg)


def _get_material(cat):
    path = "/Game/Temp/Markers/MK_" + cat
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.EditorAssetLibrary.load_asset(path)
    unreal.EditorAssetLibrary.make_directory("/Game/Temp/Markers")
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat = tools.create_asset("MK_" + cat, "/Game/Temp/Markers", unreal.Material, unreal.MaterialFactoryNew())
    r, g, b = CATEGORY_COLORS[cat]
    node = unreal.MaterialEditingLibrary.create_material_expression(
        mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
    node.constant = unreal.LinearColor(r * 2.0, g * 2.0, b * 2.0, 1.0)
    unreal.MaterialEditingLibrary.connect_material_property(node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat


def _run():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = ues.get_editor_world() if ues else None
    if world is None:
        raise RuntimeError("markers refused: no editor world is loaded.")

    package_name = world.get_outermost().get_name()
    if package_name != EXPECTED_MAP:
        raise RuntimeError("markers refused: active package is %s, expected %s" % (package_name, EXPECTED_MAP))

    landscapes = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LandscapeProxy)
    if len(landscapes) != 1:
        raise RuntimeError("markers refused: expected exactly 1 LandscapeProxy.")
    landscape = landscapes[0]
    loc = landscape.get_actor_location()
    scl = landscape.get_actor_scale3d()
    yaw = landscape.get_actor_rotation().yaw

    def near(a, b, eps):
        return all(abs(a[i] - b[i]) <= eps for i in range(3))

    if not near((loc.x, loc.y, loc.z), CANON_LOC, 0.05):
        raise RuntimeError("markers refused: landscape location %.2f,%.2f,%.2f != canonical" % (loc.x, loc.y, loc.z))
    if not near((scl.x, scl.y, scl.z), CANON_SCALE, 0.01):
        raise RuntimeError("markers refused: landscape scale mismatch")
    if min(abs(yaw - 180.0), abs(yaw + 180.0)) > 0.5:
        raise RuntimeError("markers refused: landscape yaw %.2f != 180" % yaw)

    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in actor_sub.get_all_level_actors():
        if a.get_actor_label().startswith("MRK_"):
            raise RuntimeError("markers refused: '%s' already exists." % a.get_actor_label())

    with open(MARKER_JSON, "r") as fh:
        markers = json.load(fh)

    sphere_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Sphere")
    mats = {cat: _get_material(cat) for cat in set(m["cat"] for m in markers)}

    spawned = {}
    labelled = {}
    for m in markers:
        cat = m["cat"]
        pos = unreal.Vector(m["x"], m["y"], m["z"])
        actor = actor_sub.spawn_actor_from_object(sphere_mesh, pos, unreal.Rotator(0.0, 0.0, 0.0))
        actor.set_actor_label("MRK_" + m["label"])
        actor.set_actor_scale3d(unreal.Vector(SPHERE_SCALE, SPHERE_SCALE, SPHERE_SCALE))
        comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        if comp is not None:
            comp.set_material(0, mats[cat])
        try:
            actor_sub.set_actor_folder_path(actor, CATEGORY_FOLDER[cat])
        except Exception as e:
            _log("folder skipped for %s: %s" % (m["label"], e))
        spawned[cat] = spawned.get(cat, 0) + 1

        if cat in LABELLED_CATS:
            tpos = unreal.Vector(m["x"], m["y"], m["z"] + 300.0)
            tr = actor_sub.spawn_actor_from_class(unreal.TextRenderActor, tpos, unreal.Rotator(0.0, 0.0, 0.0))
            short = m["label"].split("_", 1)[-1]
            tr.set_actor_label("MRKL_" + m["label"])
            trc = tr.get_component_by_class(unreal.TextRenderComponent)
            if trc is not None:
                trc.set_editor_property("text", short)
                trc.set_editor_property("world_size", 500.0)
            try:
                actor_sub.set_actor_folder_path(tr, CATEGORY_FOLDER[cat])
            except Exception:
                pass
            labelled[cat] = labelled.get(cat, 0) + 1

    total = sum(spawned.values())
    for cat in sorted(spawned):
        _log("COUNT_%s=%d (labelled=%d)" % (cat, spawned[cat], labelled.get(cat, 0)))
    _log("TOTAL=%d" % total)

    level_package = world.get_outermost()
    saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_package], False)
    if not saved:
        saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_package], True)
    _log("SAVED=%s" % saved)
    if not saved:
        raise RuntimeError("saving the target level failed.")

    post_loc = landscapes[0].get_actor_location()
    post_scl = landscapes[0].get_actor_scale3d()
    unchanged = near((post_loc.x, post_loc.y, post_loc.z), CANON_LOC, 0.05) and near((post_scl.x, post_scl.y, post_scl.z), CANON_SCALE, 0.01)
    _log("LANDSCAPE_UNCHANGED=%s" % unchanged)
    if not unchanged:
        raise RuntimeError("landscape transform changed unexpectedly.")

    unreal.SystemLibrary.execute_console_command(world, "MAP CHECKDEP NOCLEARLOG")
    _log("SUCCESS")


try:
    _run()
except Exception:
    unreal.log_error("JPARK_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
