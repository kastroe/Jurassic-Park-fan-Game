import unreal


# TEST MAP SETUP ONLY
# Creates a new empty test map and places the existing movie-map reference.
# Landscape creation/import remains a manual Landscape Editor operation because
# this UE 5.8 runtime does not expose a safe Landscape creation API.

TEST_MAP_PATH = "/Game/Maps/JP_MovieMap_Landscape_Test"
REFERENCE_ASSET_PATH = "/Game/JPGenerated/JP_MovieMap_Reference"
REFERENCE_LABEL = "JP_MovieMap_Reference"

REFERENCE_LOCATION = unreal.Vector(-19000.0, -20000.0, 21635.0)
REFERENCE_ROTATION = unreal.Rotator(0.0, 90.0, 180.0)
REFERENCE_SCALE = unreal.Vector(-1.05, 1.05, 1.05)


if unreal.EditorAssetLibrary.does_asset_exist(TEST_MAP_PATH + "." + TEST_MAP_PATH.rsplit("/", 1)[-1]):
    raise RuntimeError("Test map already exists; refusing to overwrite: %s" % TEST_MAP_PATH)

world = unreal.EditorLevelLibrary.new_level(TEST_MAP_PATH)
if world is None:
    raise RuntimeError("Could not create test map: %s" % TEST_MAP_PATH)

reference_mesh = unreal.EditorAssetLibrary.load_asset(REFERENCE_ASSET_PATH)
if reference_mesh is None or not isinstance(reference_mesh, unreal.StaticMesh):
    raise RuntimeError("Movie-map reference StaticMesh could not be loaded: %s" % REFERENCE_ASSET_PATH)

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
reference_actor = actor_subsystem.spawn_actor_from_class(
    unreal.StaticMeshActor,
    REFERENCE_LOCATION,
    REFERENCE_ROTATION,
)
if reference_actor is None:
    raise RuntimeError("Could not spawn movie-map reference actor in the test map.")

reference_actor.set_actor_label(REFERENCE_LABEL)
reference_actor.static_mesh_component.set_static_mesh(reference_mesh)
reference_actor.set_actor_scale3d(REFERENCE_SCALE)

if unreal.EditorLevelLibrary.save_current_level() is not True:
    raise RuntimeError("Could not save the new test map.")

unreal.log("JP MOVIE MAP TEST MAP READY: path=%s reference=%s location=%s rotation=%s scale=%s" % (
    TEST_MAP_PATH,
    REFERENCE_LABEL,
    REFERENCE_LOCATION,
    REFERENCE_ROTATION,
    REFERENCE_SCALE,
))
unreal.log("JP MOVIE MAP TEST MAP NEXT: import Reference/MovieMapLandscape/JP_MovieMap_Height_694x946_16bit.png manually in Landscape mode")
