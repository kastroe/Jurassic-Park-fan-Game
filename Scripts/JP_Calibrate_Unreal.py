"""
JP_Calibrate_Unreal.py  — run inside Unreal Editor Python
Queries JPWorldQueryLibrary at canonical markers and compares
against offline R16 values for each candidate mapping.

Run via:
  1) Editor → Window → Output Log → paste contents
  2) Or: ExecuteFile command in console

Use alongside JP_Calibrate_Offline.py output to find correct mapping.
"""

import sys
import os
sys.path.append(os.path.join(os.getcwd(), "Scripts"))

try:
    import unreal
except ImportError:
    print("ERROR: Must be run inside Unreal Editor Python interpreter.")
    sys.exit(1)

try:
    from JPWorldQueryLibrary import get_height_at_location, get_height_at_path_point
except ImportError:
    print("ERROR: Cannot import JPWorldQueryLibrary.")
    print("Ensure Scripts/ folder is on sys.path and module is accessible.")
    sys.exit(1)

MARKERS = {
    "Visitor Center": (165000, 215000),
    "Main Gate": (203000, 213000),
    "Helipad": (170500, 135500),
    "Brachiosaurus": (205000, 155000),
    "T-Rex Paddock": (285000, 236000),
    "Port": (370000, 232000),
}

# Offline R16 height estimates for each marker under different mappings.
# Source: JP_Calibrate_Offline.py output (run offline first).
# Format: mapping_name -> { marker_name: height_cm }
# You will fill these in after running the offline calibration script.
# For now, leave empty or paste results from offline run.

# Once you have the offline values, uncomment and fill in the correct mapping:
# OFFLINE_HEIGHTS = {
#     "A_direct": { "Visitor Center": 17800.0, ... },
#     ...
# }


def main():
    print("=" * 80)
    print("UNREAL HEIGHT CALIBRATION — JP_Calibrate_Unreal.py")
    print("=" * 80)

    unreal.log("=" * 80)
    unreal.log("UNREAL HEIGHT CALIBRATION")
    unreal.log("=" * 80)

    results = {}

    for name, (wx, wy) in MARKERS.items():
        h = get_height_at_location(wx, wy, 13000)
        hpp = get_height_at_path_point(wx, wy, 13000, 0.0, False)

        unreal.log("%-20s (%8.1f, %8.1f): height=%.1f cm (%.1f m)" % (
            name, wx, wy, h, h / 100.0))
        print("%-20s (%8.1f, %8.1f): height=%.1f cm (%.1f m) [path_point=%.1f]" % (
            name, wx, wy, h, h / 100.0, hpp))

        results[name] = {
            "world_x": wx,
            "world_y": wy,
            "unreal_height_cm": round(h, 1),
            "unreal_height_m": round(h / 100.0, 1),
            "path_point_cm": round(hpp, 1),
        }

    # Write JSON for easy comparison
    import json
    json_path = os.path.join(os.getcwd(), "Scripts", "_calibration_unreal.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print()
    print("Results written to: %s" % json_path)
    unreal.log("Results written to: %s" % json_path)

    print()
    print("=" * 80)
    print("NEXT: Compare these heights against JP_Calibrate_Offline.py output.")
    print("Find which mapping (A-F) and landscape location produce matching heights.")
    print("=" * 80)
    unreal.log("=" * 80)
    unreal.log("Compare against JP_Calibrate_Offline.py output.")
    unreal.log("=" * 80)


if __name__ == "__main__":
    main()
