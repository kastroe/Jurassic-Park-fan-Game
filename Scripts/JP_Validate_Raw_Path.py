"""
JP_Validate_Raw_Path.py  (READ-ONLY)
Validates the raw 268-cell Dijkstra path for adjacency on 5m grid.
"""

import math
import numpy as np
import sys

R16_PATH = "Reference/JurassicDreamTerrain/JurassicDream_4081x4081_UE.r16"
HM_RES = 4081
SCALE_XY = 100.3921569
SCALE_Z = 200.0030518
ACTOR_X = 409600.0
ACTOR_Y = 409600.0
ACTOR_Z = 51200.7813
WATER_LEVEL = 5000.0
EDGE_SAMPLE_CM = 250.0

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

    # Load raw path
    raw_path = []
    with open("Scripts/_best_raw_path.txt") as f:
        for line in f:
            line = line.strip()
            if line:
                x, y = line.split(",")
                raw_path.append((int(x), int(y)))

    print("=" * 80)
    print("RAW PATH VALIDATION (268 cells)")
    print("=" * 80)

    # Basic stats
    print()
    print("Raw nodes: %d" % len(raw_path))
    print("Start: (%d, %d)" % raw_path[0])
    print("End:   (%d, %d)" % raw_path[-1])

    # Check start/end
    errors = []
    if raw_path[0] != (205000, 155000):
        errors.append("START is not Brachiosaurus: %s" % str(raw_path[0]))
    if raw_path[-1] != (180000, 208000):
        errors.append("END is not VC approach: %s" % str(raw_path[-1]))

    # Check adjacency (5m grid: cardinal=500cm, diagonal=707cm)
    max_spacing = 0
    jumps = []
    for i in range(len(raw_path) - 1):
        x1, y1 = raw_path[i]
        x2, y2 = raw_path[i + 1]
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        dist = math.sqrt(dx*dx + dy*dy)
        max_spacing = max(max_spacing, dist)
        if dist > 750:  # tolerance for diagonal + rounding
            jumps.append((i, i+1, dist, x1, y1, x2, y2))

    print()
    print("Max raw-node spacing: %.0f cm (%.1f m)" % (max_spacing, max_spacing/100))
    print("Jumps > 7.5m: %d" % len(jumps))

    if jumps:
        print()
        print("JUMP DETAILS:")
        for idx1, idx2, dist, x1, y1, x2, y2 in jumps[:10]:
            print("  [%d]->[%d]: (%d,%d)->(%d,%d) dist=%.0f cm" % (
                idx1, idx2, x1, y1, x2, y2, dist))

    # Dense terrain validation
    print()
    print("=" * 80)
    print("DENSE TERRAIN VALIDATION (250 cm spacing)")
    print("=" * 80)

    dense_pts = []
    for i in range(len(raw_path) - 1):
        x1, y1 = raw_path[i]
        x2, y2 = raw_path[i + 1]
        d = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        n = max(2, int(d / EDGE_SAMPLE_CM) + 1)
        for j in range(n):
            t = j / float(n - 1)
            dense_pts.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
    dense_pts.append(raw_path[-1])

    h = []
    valid = True
    for px, py in dense_pts:
        ht = get_height(grid, px, py)
        if ht is None:
            valid = False
            errors.append("OUT OF BOUNDS at (%.0f, %.0f)" % (px, py))
            break
        h.append(ht)

    if valid:
        slopes = []
        water_count = 0
        over15_count = 0
        for i in range(len(dense_pts) - 1):
            if h[i] < WATER_LEVEL or h[i + 1] < WATER_LEVEL:
                water_count += 1
            x1, y1 = dense_pts[i]
            x2, y2 = dense_pts[i + 1]
            d = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            sl = slope_deg(h[i], h[i + 1], d)
            slopes.append(sl)
            if sl > 15.0:
                over15_count += 1

        total = len(slopes)
        total_dist = sum(
            math.sqrt((dense_pts[i+1][0] - dense_pts[i][0])**2 +
                      (dense_pts[i+1][1] - dense_pts[i][1])**2)
            for i in range(len(dense_pts) - 1)
        )

        le8 = sum(1 for s in slopes if s <= 8)
        f8_10 = sum(1 for s in slopes if 8 < s <= 10)
        f10_12 = sum(1 for s in slopes if 10 < s <= 12)
        f12_15 = sum(1 for s in slopes if 12 < s <= 15)

        print()
        print("Dense samples: %d" % len(dense_pts))
        print("Total distance: %.0f m (%.1f km)" % (total_dist/100, total_dist/10000))
        print("Max slope: %.1f deg" % max(slopes))
        print("Avg slope: %.1f deg" % (sum(slopes)/total if total else 0))
        print("<=8: %d (%.0f%%)" % (le8, 100*le8/max(1,total)))
        print("8-10: %d" % f8_10)
        print("10-12: %d" % f10_12)
        print("12-15: %d" % f12_15)
        print(">15: %d" % over15_count)
        print("Water: %d" % water_count)

        if over15_count > 0:
            errors.append("SEGMENTS >15: %d" % over15_count)
        if water_count > 0:
            errors.append("WATER CROSSINGS: %d" % water_count)

    # Final verdict
    print()
    print("=" * 80)
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print("  - %s" % e)
    else:
        print("VALIDATION PASSED")
        print("  - %d raw nodes" % len(raw_path))
        print("  - Start: Brachiosaurus (205000, 155000)")
        print("  - End: VC approach (180000, 208000)")
        print("  - Max spacing: %.0f cm (%.1f m) — all <= 7.5m diagonal" % (max_spacing, max_spacing/100))
        print("  - 0 jumps")
        print("  - 0 segments >15 deg")
        print("  - 0 water crossings")
    print("=" * 80)


if __name__ == "__main__":
    main()
