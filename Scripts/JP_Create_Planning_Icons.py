"""
JP_Create_Planning_Icons.py
Create unlit colored planning icons for macro-layout.
Creates 3 unlit materials (BLUE/GREEN/RED), applies to JP93_ICON_* actors,
and increases icon size for full-island visibility.
"""

import traceback
import unreal


MAP = "/Game/Maps/JP_JurassicDream_Terrain_Test"
ICON_Z_OFFSET = 5000.0
ICON_SCALE = 80.0
ICON_HEIGHT = 0.5
FOLDER = "JP1993_Layout/Planning_Icons"
MAT_FOLDER = "/Game/JP1993_Layout/Planning_Icons/Materials"

# (key, tx, ty, color_name, r, g, b)
ICONS = [
    ("VisitorCenter",  165000, 215000, "Blue",   0.05, 0.35, 1.0),
    ("MainGate",       203000, 213000, "Blue",   0.05, 0.35, 1.0),
    ("Heliport",       170500, 135500, "Blue",   0.05, 0.35, 1.0),
    ("Port",           370000, 232000, "Blue",   0.05, 0.35, 1.0),
    ("Brachiosaurus",  205000, 155000, "Green",  0.0,  0.9,  0.15),
    ("Triceratops",    248500, 164000, "Green",  0.0,  0.9,  0.15),
    ("Gallimimus",     237000, 204000, "Green",  0.0,  0.9,  0.15),
    ("T-RexPaddock",   285000, 236000, "Red",    1.0,  0.1,  0.0),
    ("Dilophosaurus",  252500, 193000, "Red",    1.0,  0.1,  0.0),
    ("Velociraptor",   140000, 315000, "Red",    1.0,  0.1,  0.0),
]


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _log(msg):
    unreal.log("JPICON %s" % msg)


def _ensure_material(color_name, r, g, b):
    """Create or load an unlit solid-color material."""
    asset_name = "M_Icon_%s" % color_name
    mat_path = "%s/%s" % (MAT_FOLDER, asset_name)

    existing = unreal.EditorAssetLibrary.load_asset(mat_path)
    if existing is not None:
        _log("Material %s already exists, deleting and recreating" % asset_name)
        unreal.EditorAssetLibrary.delete_asset(mat_path)

    if not unreal.EditorAssetLibrary.does_directory_exist(MAT_FOLDER):
        unreal.EditorAssetLibrary.make_directory(MAT_FOLDER)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat = asset_tools.create_asset(
        asset_name, MAT_FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    if mat is None:
        _log("FAILED to create material %s" % asset_name)
        return None

    shading_set = False
    try:
        mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        _log("  Set shading model to MSM_UNLIT")
        shading_set = True
    except Exception as e:
        _log("WARN: shading_model MSM_UNLIT failed: %s" % str(e))

    if not shading_set:
        try:
            mat.set_editor_property('shading_model', unreal.MaterialShadingModel(0))
            _log("  Set shading model via MaterialShadingModel(0)")
            shading_set = True
        except Exception as e:
            _log("WARN: shading_model MaterialShadingModel(0) failed: %s" % str(e))

    if not shading_set:
        try:
            mat.MaterialDomain = 0
            _log("  Set MaterialDomain to 0")
        except Exception:
            pass
        try:
            mat.MaterialShadingModel = unreal.MaterialShadingModel.MSM_UNLIT
            _log("  Set MaterialShadingModel via direct attribute")
        except Exception as e:
            _log("WARN: direct attribute failed: %s" % str(e))

    color_node = unreal.MaterialEditingLibrary.create_material_expression(
        mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
    color_node.constant = unreal.LinearColor(r, g, b, 1.0)

    emissive_prop = unreal.MaterialProperty.MP_EMISSIVE_COLOR

    connected = False
    for prop in [emissive_prop]:
        try:
            unreal.MaterialEditingLibrary.connect_material_property(
                color_node, "", prop)
            _log("  Connected color to property %s" % prop)
            connected = True
            break
        except Exception as e:
            _log("WARN: connect failed with %s: %s" % (prop, str(e)))

    if not connected:
        try:
            mat.connect_material_property(color_node, "", emissive_prop)
            _log("  Connected via mat.connect_material_property")
        except Exception as e:
            _log("WARN: mat.connect also failed: %s" % str(e))

    try:
        unreal.MaterialEditingLibrary.recompile_material(mat)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(mat_path)
    _log("Created material %s (%s)" % (asset_name, color_name))
    return mat


def _run():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = ues.get_editor_world() if ues else None
    if world is None:
        raise RuntimeError("no editor world")

    pkg = world.get_outermost().get_name()
    if pkg != MAP:
        raise RuntimeError("wrong map: %s" % pkg)

    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    # collect existing JP93 markers
    markers = {}
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        if lbl.startswith("JP93_") and "ICON" not in lbl:
            markers[lbl[len("JP93_"):]] = a
    _log("Found %d JP93 markers" % len(markers))

    # delete existing icons
    deleted = 0
    for a in actor_sub.get_all_level_actors():
        if a.get_actor_label().startswith("JP93_ICON_"):
            actor_sub.destroy_actor(a)
            deleted += 1
    if deleted:
        _log("Deleted %d old icons" % deleted)

    # load sphere mesh
    sphere_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Sphere")
    if sphere_mesh is None:
        raise RuntimeError("cannot load Sphere mesh")

    # create materials
    mats = {}
    for cn, r, g, b in [
        ("Blue",  0.05, 0.35, 1.0),
        ("Green", 0.0,  0.9,  0.15),
        ("Red",   1.0,  0.1,  0.0),
    ]:
        mats[cn] = _ensure_material(cn, r, g, b)

    # create icons
    created = []
    for key, tx, ty, color_name, r, g, b in ICONS:
        m = markers.get(key)
        if m is None:
            _log("MISSING JP93_%s" % key)
            continue

        mz = m.get_actor_location().z
        lz = mz + ICON_Z_OFFSET
        loc = unreal.Vector(float(tx), float(ty), float(lz))

        actor = actor_sub.spawn_actor_from_class(
            unreal.StaticMeshActor, loc, unreal.Rotator(0, 0, 0))
        if actor is None:
            _log("FAILED %s" % key)
            continue

        actor.set_actor_label("JP93_ICON_%s" % key)
        actor.set_folder_path(FOLDER)
        actor.set_actor_scale3d(unreal.Vector(ICON_SCALE, ICON_SCALE, ICON_HEIGHT))

        smc = actor.static_mesh_component
        smc.set_static_mesh(sphere_mesh)
        smc.set_mobility(unreal.ComponentMobility.STATIC)

        mat = mats.get(color_name)
        if mat is not None:
            smc.set_material(0, mat)

        _log("ICON %s [%s] at (%.0f,%.0f,%.0f)" % (key, color_name, tx, ty, lz))
        created.append(key)

    _log("Created %d icons with unlit materials" % len(created))

    level_pkg = world.get_outermost()
    saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], False)
    if not saved:
        saved = unreal.EditorLoadingAndSavingUtils.save_packages([level_pkg], True)
    _log("SAVED=%s" % saved)
    _log("JPICON DONE")


try:
    _run()
except Exception:
    unreal.log_error("JPICON_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
