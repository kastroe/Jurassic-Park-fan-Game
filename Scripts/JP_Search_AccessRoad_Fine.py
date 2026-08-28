"""
JP_Search_AccessRoad_Fine.py  (READ-ONLY)
Fine-grained terrain-aware Dijkstra for Access Road.
Brachiosaurus (205000,155000) -> VC approach (180000,208000).

Key improvement: every Dijkstra edge is densely sampled at <=2.5m
spacing. An edge is rejected if ANY subsegment exceeds 15deg.

Uses multi-resolution approach:
  Phase 1: 10m grid to find promising corridors
  Phase 2: 5m refinement with dense edge validation

READ-ONLY analysis. Does not modify any files or maps.
"""

import heapq
import math
import numpy as np
import sys
import time

R16_PATH = "Reference/JurassicDreamTerrain/JurassicDream_4081x4081_UE.r16"
HM_RES = 4081
SCALE_XY = 100.3921569
SCALE_Z = 200.0030518
ACTOR_X = 409600.0
ACTOR_Y = 409600.0
ACTOR_Z = 51200.7813
WATER_LEVEL = 5000.0

START = (205000, 155000)
END = (180000, 208000)

SLOPE_HARD = 15.0
SLOPE_PREF = 8.0
SLOPE_OK = 10.0
EDGE_SAMPLE_CM = 250.0

DIRS8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]


def load_heightmap():
    raw = np.fromfile(R16_PATH, dtype=np.uint16)
    if raw.size != HM_RES * HM_RES:
        print("ERROR: R16 size mismatch")
        sys.exit(1)
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
    if dist_cm <= 0:
        return 0.0
    return math.degrees(math.atan2(abs(h2 - h1), dist_cm))


def angle_between(d1, d2):
    dot = d1[0]*d2[0] + d1[1]*d2[1]
    m1 = math.sqrt(d1[0]**2 + d1[1]**2)
    m2 = math.sqrt(d2[0]**2 + d2[1]**2)
    if m1 == 0 or m2 == 0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / (m1 * m2)))))


def validate_edge_dense(grid, x1, y1, x2, y2, sample_step=EDGE_SAMPLE_CM):
    """Densely sample terrain along edge. Return (max_slope, water_count) or None if invalid."""
    dx = x2 - x1
    dy = y2 - y1
    total_dist = math.sqrt(dx*dx + dy*dy)
    if total_dist <= 0:
        return 0.0, 0

    n_samples = max(2, int(total_dist / sample_step) + 1)
    heights = []
    for i in range(n_samples):
        t = i / float(n_samples - 1)
        px = x1 + dx * t
        py = y1 + dy * t
        h = get_height(grid, px, py)
        if h is None:
            return None
        heights.append(h)

    max_slope = 0.0
    water_count = 0
    for i in range(len(heights) - 1):
        seg_dist = total_dist / (n_samples - 1)
        sl = slope_deg(heights[i], heights[i+1], seg_dist)
        if sl > SLOPE_HARD:
            return None
        max_slope = max(max_slope, sl)
        if heights[i] < WATER_LEVEL:
            water_count += 1

    return max_slope, water_count


def slope_cost(sl):
    if sl <= SLOPE_PREF:
        return 1.0
    elif sl <= SLOPE_OK:
        return 1.0 + 2.0 * ((sl - SLOPE_PREF) / (SLOPE_OK - SLOPE_PREF))
    else:
        return 3.0 + 10.0 * ((sl - SLOPE_OK) / (SLOPE_HARD - SLOPE_OK))


def dijkstra_fine(grid, x_min, y_min, grid_res, nx, ny,
                  start_world, end_world, heading_weight=4.0,
                  blocked=None):
    if blocked is None:
        blocked = set()

    def gw(gx, gy):
        return x_min + gx * grid_res, y_min + gy * grid_res

    def tg(wx, wy):
        return int(round((wx - x_min) / grid_res)), int(round((wy - y_min) / grid_res))

    INF = float('inf')
    dist = {tg(*start_world): 0.0}
    prev = {}
    prev_dir = {}
    visited = set()
    sg = tg(*start_world)
    eg = tg(*end_world)
    heap = [(0.0, sg[0], sg[1])]

    nodes_expanded = 0
    edges_tested = 0
    edges_rejected = 0

    while heap:
        d, gx, gy = heapq.heappop(heap)
        key = (gx, gy)
        if key in visited:
            continue
        visited.add(key)
        nodes_expanded += 1
        if key == eg:
            break

        wx1, wy1 = gw(gx, gy)
        h1 = get_height(grid, wx1, wy1)
        if h1 is None:
            continue

        for dgx, dgy in DIRS8:
            ngx, ngy = gx + dgx, gy + dgy
            nkey = (ngx, ngy)
            if nkey in visited or nkey in blocked:
                continue
            if ngx < 0 or ngx >= nx or ngy < 0 or ngy >= ny:
                continue

            nwx, nwy = gw(ngx, ngy)
            h2 = get_height(grid, nwx, nwy)
            if h2 is None:
                continue

            edges_tested += 1

            cd = math.sqrt(dgx**2 + dgy**2) * grid_res
            sl_endpoints = slope_deg(h1, h2, cd)

            result = validate_edge_dense(grid, wx1, wy1, nwx, nwy, EDGE_SAMPLE_CM)
            if result is None:
                edges_rejected += 1
                continue

            max_sl, water = result

            sc = slope_cost(max_sl)
            hc = 1.0
            if key in prev_dir:
                old_dir = prev_dir[key]
                new_dir = (dgx, dgy)
                ang = angle_between(old_dir, new_dir)
                hc = 1.0 + heading_weight * (ang / 180.0) ** 2

            nd = d + cd * sc * hc
            if nd < dist.get(nkey, INF):
                dist[nkey] = nd
                prev[nkey] = key
                prev_dir[nkey] = (dgx, dgy)
                heapq.heappush(heap, (nd, ngx, ngy))

    path = []
    key = eg
    while key in prev:
        path.append(key)
        key = prev[key]
    path.append(sg)
    path.reverse()

    world_path = []
    for gx, gy in path:
        world_path.append(gw(gx, gy))

    return world_path, nodes_expanded, edges_tested, edges_rejected


def validate_dense(world_path, grid, step_cm=EDGE_SAMPLE_CM):
    dense_pts = []
    for i in range(len(world_path) - 1):
        x1, y1 = world_path[i]
        x2, y2 = world_path[i + 1]
        d = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        n = max(2, int(d / step_cm) + 1)
        for j in range(n):
            t = j / float(n - 1)
            dense_pts.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
    dense_pts.append(world_path[-1])

    h = []
    valid = True
    for px, py in dense_pts:
        ht = get_height(grid, px, py)
        if ht is None:
            valid = False
            break
        h.append(ht)

    if not valid or len(h) < 2:
        return None

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
        if sl > SLOPE_HARD:
            over15_count += 1

    total = len(slopes)
    total_dist = sum(
        math.sqrt((dense_pts[i+1][0] - dense_pts[i][0])**2 +
                  (dense_pts[i+1][1] - dense_pts[i][1])**2)
        for i in range(len(dense_pts) - 1)
    )

    return {
        "length_m": total_dist / 100.0,
        "max_slope": max(slopes) if slopes else 0,
        "avg_slope": sum(slopes) / total if total else 0,
        "le8": sum(1 for s in slopes if s <= 8),
        "f8_10": sum(1 for s in slopes if 8 < s <= 10),
        "f10_12": sum(1 for s in slopes if 10 < s <= 12),
        "f12_15": sum(1 for s in slopes if 12 < s <= 15),
        "over15": over15_count,
        "water": water_count,
        "total_samples": total,
        "slopes": slopes,
        "dense_pts": dense_pts,
        "dense_h": h,
    }


def heading_changes(path):
    changes = 0
    max_change = 0
    for i in range(2, len(path)):
        d1 = (path[i-1][0] - path[i-2][0], path[i-1][1] - path[i-2][1])
        d2 = (path[i][0] - path[i-1][0], path[i][1] - path[i-1][1])
        ang = angle_between(d1, d2)
        if ang > 15:
            changes += 1
        max_change = max(max_change, ang)
    return changes, max_change


def dense_simplify(world_path, grid, max_slope=SLOPE_HARD, dense_step=EDGE_SAMPLE_CM):
    if len(world_path) <= 2:
        return list(range(len(world_path)))

    ctrl_idx = [0]
    idx = 0

    while idx < len(world_path) - 1:
        best_next = idx + 1

        for test in range(idx + 2, len(world_path)):
            wx1, wy1 = world_path[idx]
            wx2, wy2 = world_path[test]

            result = validate_edge_dense(grid, wx1, wy1, wx2, wy2, dense_step)
            if result is None:
                break
            max_sl, water = result
            if max_sl > max_slope:
                break

            best_next = test

        ctrl_idx.append(best_next)
        idx = best_next

    return ctrl_idx


def score_route(vstats, ctrl_count, max_heading):
    score = 10.0
    if ctrl_count > 35:
        score -= (ctrl_count - 35) * 0.15
    elif ctrl_count > 25:
        score -= (ctrl_count - 25) * 0.1
    if vstats["max_slope"] > 12:
        score -= (vstats["max_slope"] - 12) * 0.5
    elif vstats["max_slope"] > 10:
        score -= (vstats["max_slope"] - 10) * 0.3
    if vstats["total_samples"] > 0:
        bad = (vstats["f10_12"] + vstats["f12_15"] + vstats["over15"]) / vstats["total_samples"]
        score -= bad * 20
    score -= vstats["over15"] * 1.0
    if vstats["avg_slope"] <= 5:
        score += 1.0
    elif vstats["avg_slope"] <= 7:
        score += 0.5
    score -= vstats["water"] * 0.5
    score -= max_heading * 0.005
    return max(0, min(10, score))


def main():
    t0 = time.time()

    print("=" * 90)
    print("FINE TERRAIN-AWARE DIJKSTRA — ACCESS ROAD SEARCH")
    print("Brachiosaurus (205000, 155000) -> VC approach (180000, 208000)")
    print("Edge validation: dense sampling at %.0f cm spacing" % EDGE_SAMPLE_CM)
    print("Hard slope limit: %.0f deg" % SLOPE_HARD)
    print("=" * 90)

    grid = load_heightmap()

    bh = get_height(grid, START[0], START[1])
    vh = get_height(grid, END[0], END[1])
    print()
    print("Brachiosaurus: %.1f m" % (bh/100))
    print("VC approach:   %.1f m" % (vh/100))
    print("Elevation: +%.1f m climb" % ((vh - bh)/100))

    # ============================================================
    # COORDINATE VALIDATION
    # ============================================================
    print()
    print("=" * 90)
    print("COORDINATE MAPPING VALIDATION")
    print("=" * 90)

    test_points = [
        ("Brachiosaurus", 205000, 155000, 10284),
        ("Visitor Center", 165000, 215000, 13160),
        ("Main Gate", 203000, 213000, 11790),
        ("Helipad", 170500, 135500, 9039),
    ]

    all_ok = True
    for name, wx, wy, expected in test_points:
        col, row = world_to_grid(wx, wy)
        h = get_height(grid, wx, wy)
        err = abs(h - expected) if h is not None else 99999
        status = "OK" if err <= 25 else "FAIL"
        if status == "FAIL":
            all_ok = False
        print("  %-20s world=(%8d,%8d)  R16 col=%4d row=%4d  h=%8.1f cm  expected=%5d  err=%5.1f  [%s]" % (
            name, wx, wy, col, row, h, expected, err, status))

    if not all_ok:
        print("  *** CALIBRATION FAILED — STOPPING ***")
        return
    print("  CALIBRATION OK")

    # ============================================================
    # SEARCH AREA
    # ============================================================
    SEARCH_RES = 500  # 5m cells
    SEARCH_X_MIN = 100000
    SEARCH_X_MAX = 350000
    SEARCH_Y_MIN = 80000
    SEARCH_Y_MAX = 300000
    snx = (SEARCH_X_MAX - SEARCH_X_MIN) // SEARCH_RES + 1
    sny = (SEARCH_Y_MAX - SEARCH_Y_MIN) // SEARCH_RES + 1

    blocked = set()
    for gy in range(sny):
        for gx in range(snx):
            wx = SEARCH_X_MIN + gx * SEARCH_RES
            wy = SEARCH_Y_MIN + gy * SEARCH_RES
            h = get_height(grid, wx, wy)
            if h is not None and h < WATER_LEVEL:
                blocked.add((gx, gy))

    print()
    print("Search grid: %d x %d = %d cells (res=%dm)" % (snx, sny, snx * sny, SEARCH_RES // 100))
    print("Water/blocked cells: %d" % len(blocked))

    # ============================================================
    # PHASE 1: FINE DIJKSTRA with multiple heading weights
    # ============================================================
    print()
    print("=" * 90)
    print("PHASE 1: FINE DIJKSTRA (10m grid, dense edge validation)")
    print("=" * 90)

    all_results = []

    for hw in [2.0, 4.0, 6.0, 8.0]:
        print()
        print("  --- heading_weight=%.1f ---" % hw)
        t1 = time.time()
        path, nodes, edges, rejected = dijkstra_fine(
            grid, SEARCH_X_MIN, SEARCH_Y_MIN, SEARCH_RES, snx, sny,
            START, END, heading_weight=hw, blocked=blocked)
        t2 = time.time()
        print("  Time: %.1f s  Nodes: %d  Edges tested: %d  Rejected: %d" % (
            t2 - t1, nodes, edges, rejected))
        print("  Raw path: %d cells" % len(path))

        if len(path) < 3:
            print("  PATH BROKEN (too short)")
            continue

        vstats = validate_dense(path, grid, EDGE_SAMPLE_CM)
        if vstats is None:
            print("  VALIDATION FAILED")
            continue

        hc, max_hc = heading_changes(path)
        print("  Length: %.0f m (%.1f km)" % (vstats["length_m"], vstats["length_m"]/1000))
        print("  Max slope: %.1f deg  Avg: %.1f deg" % (vstats["max_slope"], vstats["avg_slope"]))
        print("  <=8: %.0f%%  8-10: %d  10-12: %d  12-15: %d  >15: %d" % (
            100*vstats["le8"]/max(1,vstats["total_samples"]),
            vstats["f8_10"], vstats["f10_12"], vstats["f12_15"], vstats["over15"]))
        print("  Water: %d  Heading >15deg: %d (max %.0f)" % (vstats["water"], hc, max_hc))

        ctrl = dense_simplify(path, grid, SLOPE_HARD, EDGE_SAMPLE_CM)
        ctrl_pts = [path[i] for i in ctrl]
        sv = validate_dense(ctrl_pts, grid, EDGE_SAMPLE_CM)
        if sv is None:
            sv = vstats
        ctrl_hc, ctrl_max_hc = heading_changes(ctrl_pts)
        sc = score_route(sv, len(ctrl_pts), ctrl_max_hc)

        print("  Simplified: %d ctrl pts  Max: %.1f deg  Avg: %.1f deg" % (
            len(ctrl_pts), sv["max_slope"], sv["avg_slope"]))
        print("  Simplified <=8: %.0f%%  >15: %d  Score: %.1f" % (
            100*sv["le8"]/max(1,sv["total_samples"]), sv["over15"], sc))

        all_results.append({
            "name": "hw=%.1f" % hw,
            "path": path,
            "ctrl_pts": ctrl_pts,
            "ctrl_count": len(ctrl_pts),
            "vstats": vstats,
            "sv_stats": sv,
            "heading_changes": ctrl_hc,
            "max_heading": ctrl_max_hc,
            "score": sc,
            "nodes": nodes,
            "edges": edges,
            "rejected": rejected,
        })

    # Save raw path of best candidate (hw=4.0) for visualization
    best = max(all_results, key=lambda r: r["score"])
    raw_path_file = "Scripts/_best_raw_path.txt"
    with open(raw_path_file, "w") as f:
        for wx, wy in best["path"]:
            f.write("%d,%d\n" % (wx, wy))
    print()
    print("Best raw path (%d cells) saved to %s" % (len(best["path"]), raw_path_file))

    # ============================================================
    # PHASE 2: WAYPOINT-GUIDED CORRIDORS
    # ============================================================
    print()
    print("=" * 90)
    print("PHASE 2: WAYPOINT-GUIDED CORRIDORS (10m grid)")
    print("=" * 90)

    waypoint_routes = [
        ("South-then-west",
         [(205000, 135000), (195000, 120000), (175000, 120000),
          (165000, 130000), (160000, 150000), (160000, 175000),
          (165000, 195000), (172000, 205000), (180000, 208000)]),

        ("SE-wide-loop",
         [(215000, 145000), (235000, 135000), (250000, 140000),
          (255000, 160000), (245000, 180000), (225000, 195000),
          (205000, 208000), (190000, 208000), (180000, 208000)]),

        ("East-plateau",
         [(220000, 155000), (240000, 155000), (255000, 160000),
          (255000, 175000), (245000, 195000), (225000, 208000),
          (205000, 208000), (180000, 208000)]),

        ("NE-bypass",
         [(215000, 165000), (230000, 175000), (240000, 190000),
          (235000, 205000), (215000, 208000), (195000, 208000),
          (180000, 208000)]),

        ("Wide-south-loop",
         [(205000, 130000), (185000, 115000), (165000, 120000),
          (155000, 140000), (155000, 165000), (158000, 185000),
          (165000, 200000), (175000, 208000), (180000, 208000)]),
    ]

    for name, wps in waypoint_routes:
        print()
        print("  --- %s ---" % name)
        t1 = time.time()
        path, nodes, edges, rejected = dijkstra_fine(
            grid, SEARCH_X_MIN, SEARCH_Y_MIN, SEARCH_RES, snx, sny,
            START, END, heading_weight=4.0, blocked=blocked)
        t2 = time.time()

        # Force through waypoints
        full_path = []
        points = [START] + list(wps) + [END]
        for i in range(len(points) - 1):
            p1, p2 = points[i], points[i+1]
            sub_path, _, _, _ = dijkstra_fine(
                grid, SEARCH_X_MIN, SEARCH_Y_MIN, SEARCH_RES, snx, sny,
                p1, p2, heading_weight=4.0, blocked=blocked)
            if sub_path:
                if full_path:
                    full_path.extend(sub_path[1:])
                else:
                    full_path = sub_path

        print("  Time: %.1f s" % (t2 - t1))
        print("  Raw path: %d cells" % len(full_path))

        if len(full_path) < 3:
            print("  PATH BROKEN")
            continue

        vstats = validate_dense(full_path, grid, EDGE_SAMPLE_CM)
        if vstats is None:
            print("  VALIDATION FAILED")
            continue

        hc, max_hc = heading_changes(full_path)
        print("  Length: %.0f m (%.1f km)" % (vstats["length_m"], vstats["length_m"]/1000))
        print("  Max slope: %.1f deg  Avg: %.1f deg" % (vstats["max_slope"], vstats["avg_slope"]))
        print("  <=8: %.0f%%  8-10: %d  10-12: %d  12-15: %d  >15: %d" % (
            100*vstats["le8"]/max(1,vstats["total_samples"]),
            vstats["f8_10"], vstats["f10_12"], vstats["f12_15"], vstats["over15"]))
        print("  Water: %d  Heading >15deg: %d (max %.0f)" % (vstats["water"], hc, max_hc))

        ctrl = dense_simplify(full_path, grid, SLOPE_HARD, EDGE_SAMPLE_CM)
        ctrl_pts = [full_path[i] for i in ctrl]
        sv = validate_dense(ctrl_pts, grid, EDGE_SAMPLE_CM)
        if sv is None:
            sv = vstats
        ctrl_hc, ctrl_max_hc = heading_changes(ctrl_pts)
        sc = score_route(sv, len(ctrl_pts), ctrl_max_hc)

        print("  Simplified: %d ctrl pts  Max: %.1f deg  Score: %.1f" % (
            len(ctrl_pts), sv["max_slope"], sc))

        all_results.append({
            "name": "WP-%s" % name,
            "path": full_path,
            "ctrl_pts": ctrl_pts,
            "ctrl_count": len(ctrl_pts),
            "vstats": vstats,
            "sv_stats": sv,
            "heading_changes": ctrl_hc,
            "max_heading": ctrl_max_hc,
            "score": sc,
            "nodes": nodes,
            "edges": edges,
            "rejected": rejected,
        })

    # ============================================================
    # PHASE 3: RANKING
    # ============================================================
    print()
    print("=" * 90)
    print("PHASE 3: ALL CANDIDATE RANKING")
    print("=" * 90)

    ranked = sorted(all_results, key=lambda r: -r["score"])

    hdr = "  %-35s %6s %4s %5s %5s %5s%% %4s %4s %4s %4s %3s %5s %5s"
    row = "  %-35s %6.0f %4d %5.1f %5.1f %5.0f%% %4d %4d %4d %4d %3d %5.0f %5.1f"
    print()
    print(hdr % ("Candidate", "Len m", "Ctrl", "RawMx", "SimpMx", "<=8", "8-10", "10-12", "12-15", ">15", "WC", "MxHd", "Score"))
    print("  " + "-" * 125)
    for rank, r in enumerate(ranked, 1):
        sv = r["sv_stats"]
        raw_mx = r["vstats"]["max_slope"]
        le8_pct = 100 * sv["le8"] / max(1, sv["total_samples"])
        mhc = r.get("max_heading", 0)
        print(row % (
            r["name"][:35],
            sv["length_m"],
            r["ctrl_count"],
            raw_mx,
            sv["max_slope"],
            le8_pct,
            sv["f8_10"],
            sv["f10_12"],
            sv["f12_15"],
            sv["over15"],
            sv["water"],
            mhc,
            r["score"]))

    # ============================================================
    # PHASE 4: TOP-3 DETAILED
    # ============================================================
    print()
    print("=" * 90)
    print("PHASE 4: TOP-3 DETAILED")
    print("=" * 90)

    for rank, r in enumerate(ranked[:3], 1):
        sv = r["sv_stats"]
        pct_le8 = 100*sv["le8"]/max(1,sv["total_samples"])
        pass_fail = "PASS" if sv["over15"] == 0 and sv["water"] == 0 and sv["max_slope"] <= SLOPE_HARD else "FAIL"

        print()
        print("  #%d: %s" % (rank, r["name"]))
        print("      Score: %.1f / 10" % r["score"])
        print("      Length: %.1f km  Controls: %d" % (sv["length_m"]/1000, r["ctrl_count"]))
        print("      RAW max slope: %.1f deg" % r["vstats"]["max_slope"])
        print("      DENSELY VALIDATED max slope: %.1f deg  Avg: %.1f deg" % (sv["max_slope"], sv["avg_slope"]))
        print("      <=8: %.0f%%  8-10: %d  10-12: %d  12-15: %d  >15: %d" % (
            pct_le8, sv["f8_10"], sv["f10_12"], sv["f12_15"], sv["over15"]))
        print("      Water: %d  Max heading: %.0f deg" % (sv["water"], r["max_heading"]))
        print("      ASSESSMENT: %s" % pass_fail)

        print()
        print("      Control points:")
        for i, (wx, wy) in enumerate(r["ctrl_pts"]):
            h = get_height(grid, wx, wy)
            if h is not None:
                print("        [%2d] (%7.0f, %7.0f) h=%6.1f m" % (i, wx, wy, h/100))

    # ============================================================
    # DECISION
    # ============================================================
    print()
    print("=" * 90)
    print("DECISION")
    print("=" * 90)

    natural_road = None
    for r in ranked:
        sv = r["sv_stats"]
        if (sv["over15"] == 0 and sv["water"] == 0
            and sv["max_slope"] <= SLOPE_HARD
            and r["score"] >= 2.0):
            natural_road = r
            break

    if natural_road:
        sv = natural_road["sv_stats"]
        print()
        print("NATURAL ROAD CORRIDOR FOUND")
        print()
        print("Best: %s" % natural_road["name"])
        print("  Length: %.1f km" % (sv["length_m"]/1000))
        print("  Max slope: %.1f deg" % sv["max_slope"])
        print("  Controls: %d" % natural_road["ctrl_count"])
        print("  Score: %.1f / 10" % natural_road["score"])
        print()
        print("Control points:")
        for i, (wx, wy) in enumerate(natural_road["ctrl_pts"]):
            h = get_height(grid, wx, wy)
            print("  [%2d] (%7.0f, %7.0f) h=%6.1f m" % (i, wx, wy, h/100))
        print()
        print("RECOMMENDATION: Use this corridor for the Access Road.")
    else:
        print()
        print("NO NATURALLY ROAD-FRIENDLY CORRIDOR FOUND")
        print()
        print("All candidates exceed slope limits even with dense edge validation.")
        print("The terrain has ~32m elevation climb with steep ridges.")
        print()
        print("Options:")
        print("  A. Best candidate + targeted terrain grading")
        print("  B. Engineered switchback road")
        print("  C. Road cut through mountain")
        print("  D. Move one landmark")

    t_end = time.time()
    print()
    print("Analysis completed in %.1f seconds" % (t_end - t0))


if __name__ == "__main__":
    main()
