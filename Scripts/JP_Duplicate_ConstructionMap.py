"""
JP_Duplicate_ConstructionMap.py  (step 1)
Duplicate the master Jurassic Dream terrain map into an independent
JP_JurassicDream_Construction map using the supported editor API.

SAFETY:
- Master is only READ as the duplication source; not modified.
- We save ONLY the new construction package (verified by package name).
- We NEVER call load_level on a World that Python already references
  (avoids the EditorServer GC assertion that crashed the earlier draft).
- Step 2 (separate editor launch) opens the construction map for verify/save.
"""

import traceback
import unreal

MASTER_OBJ = "/Game/Maps/JP_JurassicDream_Terrain_Test.JP_JurassicDream_Terrain_Test"
CONSTRUCTION_OBJ = "/Game/Maps/JP_JurassicDream_Construction.JP_JurassicDream_Construction"
CONSTRUCTION_PKG = "/Game/Maps/JP_JurassicDream_Construction"


def _log(m):
    unreal.log("JPDUP %s" % m)


def _quit():
    try:
        unreal.SystemLibrary.quit_editor()
    except Exception:
        pass


def _run():
    EAL = unreal.EditorAssetLibrary
    if EAL.does_asset_exist(CONSTRUCTION_OBJ):
        raise RuntimeError("Construction map already exists; refusing: %s" % CONSTRUCTION_OBJ)
    if not EAL.does_asset_exist(MASTER_OBJ):
        raise RuntimeError("Master map missing: %s" % MASTER_OBJ)

    dup = EAL.duplicate_asset(MASTER_OBJ, CONSTRUCTION_OBJ)
    if dup is None:
        raise RuntimeError("duplicate_asset returned None: %s" % CONSTRUCTION_OBJ)
    _log("DUPLICATED %s -> %s" % (MASTER_OBJ, CONSTRUCTION_OBJ))

    # --- Save ONLY the new construction package (never the master) ---
    pkg_path = None
    try:
        outer = dup.get_outermost()
        pkg_path = outer.get_name()
    except Exception as e:
        _log("PKGERR %s" % e)
    _log("DUPLICATED_ASSET_OUTER_PACKAGE=%s" % pkg_path)

    if pkg_path != CONSTRUCTION_PKG:
        raise RuntimeError("Refusing to save: duplicated asset package is %s, expected %s" % (pkg_path, CONSTRUCTION_PKG))

    saved = EAL.save_asset(CONSTRUCTION_OBJ, only_if_is_dirty=False)
    _log("SAVED_%s_CONSTRUCTION=%s" % (CONSTRUCTION_PKG, saved))

    # Confirm the asset now exists as a package on disk
    _log("CONSTRUCTION_EXISTS=%s" % EAL.does_asset_exist(CONSTRUCTION_OBJ))
    _log("STEP1_DONE")


try:
    _run()
except Exception:
    unreal.log_error("JPDUP_STEP1_FAILED\n%s" % traceback.format_exc())
finally:
    _quit()
