"""
JP_Calibrate_Offline.py  (READ-ONLY)
Offline calibration: tries multiple world→heightmap mappings and
outputs raw R16 values + computed heights for each canonical marker.

Run this from the project root:
    python Scripts/JP_Calibrate_Offline.py

Compare output against JP_Calibrate_Unreal.py results.
"""

import math
import numpy as np
import sys

R16_PATH = "Reference/JurassicDreamTerrain/JurassicDream_4081x4081_UE.r16"
HM_RES = 4081

# Known canonical marker positions (world XY in cm)
MARKERS = {
    "Visitor Center":  (165000, 215000),
    "Main Gate":       (203000, 213000),
    "Helipad":         (170500, 135500),
    "Brachiosaurus":   (205000, 155000),
    "T-Rex Paddock":   (285000, 236000),
    "Port":            (370000, 232000),
}

# Candidate Landscape locations (XY only; Z is always 51200.7813)
# From C++ import code: (0, 0, 51200.7813)
# From user: (409600, 409600, 51200.78125)
CANDIDATE_LOCATIONS = [
    ("import_code (0,0)",         (0,       0,       51200.7813)),
    ("user_stated (409600,409600)", (409600, 409600, 51200.7813)),
    ("half_size (204800,204800)", (204800, 204800, 51200.7813)),
]

SCALE_XY = 100.3921569
SCALE_Z = 200.0030518


def load_r16():
    raw = np.fromfile(R16_PATH, dtype=np.uint16)
    if raw.size != HM_RES * HM_RES:
        print("ERROR: R16 size mismatch: %d" % raw.size)
        sys.exit(1)
    return raw.reshape((HM_RES, HM_RES))


def raw_to_world_z(rv, actor_z, scale_z):
    return actor_z + (float(rv) - 32768.0) * scale_z / 128.0


def try_mappings(grid, world_x, world_y, actor_loc, scale_xy, scale_z):
    """Try several mapping strategies for a single world point."""
    results = {}

    # Mapping A: Direct (current broken code)
    col_a = world_x / scale_xy
    row_a = world_y / scale_xy
    ci_a, ri_a = int(round(col_a)), int(round(row_a))
    if 0 <= ci_a < HM_RES and 0 <= ri_a < HM_RES:
        rv = int(grid[ri_a, ci_a])
        hz = raw_to_world_z(rv, actor_loc[2], scale_z)
        results["A_direct"] = (hz, ci_a, ri_a, rv)
    else:
        results["A_direct"] = (None, ci_a, ri_a, None)

    # Mapping B: Subtract actor XY, add half-size offset (no rotation)
    col_b = (world_x - actor_loc[0]) / scale_xy + (HM_RES - 1) / 2.0
    row_b = (world_y - actor_loc[1]) / scale_xy + (HM_RES - 1) / 2.0
    ci_b, ri_b = int(round(col_b)), int(round(row_b))
    if 0 <= ci_b < HM_RES and 0 <= ri_b < HM_RES:
        rv = int(grid[ri_b, ci_b])
        hz = raw_to_world_z(rv, actor_loc[2], scale_z)
        results["B_translate_offset"] = (hz, ci_b, ri_b, rv)
    else:
        results["B_translate_offset"] = (None, ci_b, ri_b, None)

    # Mapping C: Inverse 180° rotation (actor - world) + half-size
    col_c = (actor_loc[0] - world_x) / scale_xy + (HM_RES - 1) / 2.0
    row_c = (actor_loc[1] - world_y) / scale_xy + (HM_RES - 1) / 2.0
    ci_c, ri_c = int(round(col_c)), int(round(row_c))
    if 0 <= ci_c < HM_RES and 0 <= ri_c < HM_RES:
        rv = int(grid[ri_c, ci_c])
        hz = raw_to_world_z(rv, actor_loc[2], scale_z)
        results["C_rot180_offset"] = (hz, ci_c, ri_c, rv)
    else:
        results["C_rot180_offset"] = (None, ci_c, ri_c, None)

    # Mapping D: Inverse 180° rotation, no offset
    col_d = (actor_loc[0] - world_x) / scale_xy
    row_d = (actor_loc[1] - world_y) / scale_xy
    ci_d, ri_d = int(round(col_d)), int(round(row_d))
    if 0 <= ci_d < HM_RES and 0 <= ri_d < HM_RES:
        rv = int(grid[ri_d, ci_d])
        hz = raw_to_world_z(rv, actor_loc[2], scale_z)
        results["D_rot180_nooft"] = (hz, ci_d, ri_d, rv)
    else:
        results["D_rot180_nooft"] = (None, ci_d, ri_d, None)

    # Mapping E: Same as D but with row/col swapped
    col_e = (actor_loc[1] - world_y) / scale_xy
    row_e = (actor_loc[0] - world_x) / scale_xy
    ci_e, ri_e = int(round(col_e)), int(round(row_e))
    if 0 <= ci_e < HM_RES and 0 <= ri_e < HM_RES:
        rv = int(grid[ri_e, ci_e])
        hz = raw_to_world_z(rv, actor_loc[2], scale_z)
        results["E_rot180_swap"] = (hz, ci_e, ri_e, rv)
    else:
        results["E_rot180_swap"] = (None, ci_e, ri_e, None)

    # Mapping F: (world - actor) / scale, no half-size, no rotation
    col_f = world_x / scale_xy
    row_f = (HM_RES - 1) - (world_y / scale_xy)
    ci_f, ri_f = int(round(col_f)), int(round(row_f))
    if 0 <= ci_f < HM_RES and 0 <= ri_f < HM_RES:
        rv = int(grid[ri_f, ci_f])
        hz = raw_to_world_z(rv, actor_loc[2], scale_z)
        results["F_yflip"] = (hz, ci_f, ri_f, rv)
    else:
        results["F_yflip"] = (None, ci_f, ri_f, None)

    return results


def main():
    print("=" * 80)
    print("OFFLINE HEIGHTMAP CALIBRATION")
    print("=" * 80)

    grid = load_r16()
    print("R16 loaded: %d x %d, raw range %d - %d" % (
        grid.shape[0], grid.shape[1], grid.min(), grid.max()))

    for loc_name, actor_loc in CANDIDATE_LOCATIONS:
        print()
        print("=" * 80)
        print("LANDSCAPE LOCATION: %s" % loc_name)
        print("  XY=(%.1f, %.1f) Z=%.4f" % actor_loc)
        print("=" * 80)

        mapping_totals = {}
        for marker_name, (wx, wy) in MARKERS.items():
            results = try_mappings(grid, wx, wy, actor_loc, SCALE_XY, SCALE_Z)
            print()
            print("  %s (%d, %d):" % (marker_name, wx, wy))
            for mname, (hz, ci, ri, rv) in sorted(results.items()):
                if hz is not None:
                    print("    %-25s col=%4d row=%4d raw=%5d hz=%8.1f cm (%6.1f m)" % (
                        mname, ci, ri, rv, hz, hz / 100.0))
                    if mname not in mapping_totals:
                        mapping_totals[mname] = []
                    mapping_totals[mname].append((marker_name, hz))
                else:
                    print("    %-25s OUT OF BOUNDS (col=%d, row=%d)" % (mname, ci, ri))

        print()
        print("  --- Per-mapping summary ---")
        for mname in sorted(mapping_totals.keys()):
            entries = mapping_totals[mname]
            print("    %s:" % mname)
            for mname2, hz in entries:
                print("      %-20s %8.1f cm (%6.1f m)" % (mname2, hz, hz / 100.0))

    print()
    print("=" * 80)
    print("NEXT STEP: Run JP_Calibrate_Unreal.py in Unreal Editor")
    print("Compare the Unreal heights against the offline values above.")
    print("Find the mapping where offline heights match Unreal heights.")
    print("=" * 80)


if __name__ == "__main__":
    main()
