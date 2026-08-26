import unreal


TEST_MAP_PATH = "/Game/Maps/JP_JurassicDream_Terrain_Test"


if unreal.EditorAssetLibrary.does_asset_exist(
    TEST_MAP_PATH + "." + TEST_MAP_PATH.rsplit("/", 1)[-1]
):
    raise RuntimeError("Test map already exists; refusing to overwrite: %s" % TEST_MAP_PATH)

world = unreal.EditorLevelLibrary.new_level(TEST_MAP_PATH)
if world is None:
    raise RuntimeError("Could not create test map: %s" % TEST_MAP_PATH)

if unreal.EditorLevelLibrary.save_current_level() is not True:
    raise RuntimeError("Could not save the new test map.")

unreal.log("JURASSIC DREAM TERRAIN TEST MAP READY: %s" % TEST_MAP_PATH)
