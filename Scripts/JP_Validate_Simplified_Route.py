"""
JP_Validate_Simplified_Route.py  (READ-ONLY)
Validates the 24-point simplified route with dense terrain sampling.
Checks every straight segment between consecutive controls at 250cm spacing.
"""

import math
import numpy as np

R16_PATH = "Reference/JurassicDreamTerrain/JurassicDream_4081x4081_UE.r16"
HM_RES = 4081
SCALE_XY = 100.3921569
SCALE_Z = 200.0030518
ACTOR_X = 409600.0
ACTOR_Y = 409600.0
ACTOR_Z = 51200.7813
WATER_LEVEL = 5000.0
EDGE_SAMPLE_CM = 250.0

# The 24-point simplified route
ROUTE_24 = [
    ("Brachiosaurus",    205000, 155000),
    ("West-southwest",   183000, 146500),
    ("Southwest",        176500, 145000),
    ("Far-west",         150000, 173500),
    ("West-climb",       147500, 175500),
    ("Southwest-low",    141000, 181000),
    ("South",            140500, 184000),
    ("Southeast-climb",  144000, 192500),
    ("East-climb",       145000, 192000),
    ("North-climb",      145000, 200000),
    ("NE-climb-1",       145500, 200500),
    ("NE-climb-2",       148500, 200500),
    ("NE-climb-3",       148000, 199500),
    ("NE-climb-4",       148500, 199500),
    ("NE-climb-5",       148000, 198500),
    ("NE-climb-6",       149000, 198500),
    ("NE-climb-7",       148500, 198000),
    ("NE-climb-8",       149500, 198000),
    ("NE-climb-9",       149000, 197500),
    ("NE-climb-10",      148500, 197500),
    ("East-approach",    151500, 197000),
    ("NE-approach",      158000, 202500),
    ("East-VC",          179000, 207500),
    ("VC-approach-W",    180000, 208000),
]


def load_heightmap():
    raw = np.fromfile(R16_PATH, dtype=np.uint16)
    return raw.reshape((HM_RES, HM_RES))


def raw_to_world_z(rv):
    return ACTOR_Z + (float(rv) - 32768.0) * SCALE_Z / 128.0


def world_to_grid(x, y):
    col = (ACTOR_X - x) / SCALE_XY
    row = (ACTOR_Y - y) / SCALE_XY
    return int(round(col)), int(round(row))


def get_height(grid, x_cm, y_cm):
    col, row = world_to_grid(x_cm, y_cm)
    if col < 0 or col >= HM_RES or row < 0 or row >= HM_RES:
        return None
    return raw_to_world_z(int(grid[row, col]))


def slope_deg(h1, h2, dist_cm):
    if dist_cm <= 0: return 0.0
    return math.degrees(math.atan2(abs(h2 - h1), dist_cm))


def main():
    grid = load_heightmap()

    print("=" * 80)
    print("24-POINT SIMPLIFIED ROUTE VALIDATION")
    print("=" * 80)

    errors = []
    all_max_slopes = []
    all_water = 0
    all_over15 = 0
    total_dist = 0

    for i in range(len(ROUTE_24) - 1):
        n1, x1, y1 = ROUTE_24[i]
        n2, x2, y2 = ROUTE_24[i + 1]

        d = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        n_samples = max(2, int(d / EDGE_SAMPLE_CM) + 1)

        pts = []
        for j in range(n_samples):
            t = j / float(n_samples - 1)
            pts.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))

        heights = []
        for px, py in pts:
            ht = get_height(grid, px, py)
            if ht is None:
                errors.append("%s->%s: OUT OF BOUNDS at (%.0f, %.0f)" % (n1, n2, px, py))
                break
            heights.append(ht)

        if len(heights) != len(pts):
            continue

        seg_slopes = []
        seg_water = 0
        seg_over15 = 0
        for j in range(len(pts) - 1):
            if heights[j] < WATER_LEVEL or heights[j + 1] < WATER_LEVEL:
                seg_water += 1
            sl = slope_deg(heights[j], heights[j + 1], d / (n_samples - 1))
            seg_slopes.append(sl)
            if sl > 15.0:
                seg_over15 += 1

        max_sl = max(seg_slopes) if seg_slopes else 0
        all_max_slopes.append((n1, n2, max_sl, d / 100, len(pts) - 1))
        all_water += seg_water
        all_over15 += seg_over15
        total_dist += d

        status = "PASS" if max_sl <= 15.0 and seg_over15 == 0 else "FAIL"
        if seg_over15 > 0:
            errors.append("%s->%s: %d segments >15 deg" % (n1, n2, seg_over15))
        if seg_water > 0:
            errors.append("%s->%s: %d water crossings" % (n1, n2, seg_water))

    # Detailed segment report
    print()
    print("SEGMENT DETAILS:")
    print("%-20s %-20s %8s %8s %6s %6s %s" % ("From", "To", "Dist(m)", "MaxSl", ">15", "Water", "Status"))
    print("-" * 100)
    for n1, n2, max_sl, dist_m, n_samp in all_max_slopes:
        is_over = max_sl > 15.0
        print("%-20s %-20s %8.0f %6.1f %6d %6d %s" % (
            n1, n2, dist_m, max_sl, 1 if is_over else 0, 0,
            "FAIL" if is_over else "PASS"))

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("Total distance: %.0f m (%.1f km)" % (total_dist / 100, total_dist / 10000))
    print("Max slope: %.1f deg" % max(s for _, _, s, _, _ in all_max_slopes))
    print(">15 count: %d" % all_over15)
    print("Water count: %d" % all_water)

    if errors:
        print()
        print("VALIDATION FAILED:")
        for e in errors:
            print("  - %s" % e)
    else:
        print()
        print("VALIDATION PASSED")
        print("  Every segment between 24 controls passes at 250cm spacing")
        print("  Max slope <= 15 deg, 0 water crossings")
    print("=" * 80)


if __name__ == "__main__":
    main()
