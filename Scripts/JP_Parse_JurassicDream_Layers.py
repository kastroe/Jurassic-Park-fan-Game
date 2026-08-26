import json
import os
import xml.etree.ElementTree as ET

LAYERS = r"C:\Users\KASTROE\Downloads\Jurassic Dream\CRYENGINE\GameSDK\Levels\Jurassic_Dream\Layers"
OUT = r"C:\Users\KASTROE\Downloads\JurassicPark1993_FanGame_UE58\Intermediate\JPD_Markers.json"

OFFSET_CM = 409600.0


def qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )


def qrot(q, v):
    w, x, y, z = q
    qv = (0.0, v[0], v[1], v[2])
    qi = (w, -x, -y, -z)
    r = qmul(qmul(q, qv), qi)
    return (r[1], r[2], r[3])


def parse_pos(s):
    parts = [float(p) for p in s.split(",")]
    return (parts[0], parts[1], parts[2])


def parse_rot(s):
    parts = [float(p) for p in s.split(",")]
    return tuple(parts)  # CryEngine .lyr stores (w, x, y, z)


def load_layer(path):
    tree = ET.parse(path)
    nodes = {}
    order = []
    for obj in tree.getiter("Object") if hasattr(tree, "getiter") else tree.iter("Object"):
        oid = obj.get("Id")
        name = obj.get("Name") or ""
        node = {
            "id": oid,
            "name": name,
            "type": obj.get("Type"),
            "pos": parse_pos(obj.get("Pos", "0,0,0")),
            "rot": parse_rot(obj.get("Rotate", "1,0,0,0")) if obj.get("Rotate") else (1.0, 0.0, 0.0, 0.0),
            "parent": obj.get("Parent"),
            "prefab": (obj.get("Prefab") or ""),
            "geometry": (obj.get("Geometry") or ""),
            "material": (obj.get("Material") or ""),
            "entity_class": (obj.get("EntityClass") or ""),
            "children": [],
        }
        nodes[oid] = node
        order.append(node)

    roots = []
    for n in order:
        p = n["parent"]
        if p and p in nodes:
            nodes[p]["children"].append(n)
        else:
            roots.append(n)

    def resolve(n, pq):
        wq = qmul(pq, n["rot"]) if n["rot"] else pq
        rp = qrot(pq, n["pos"])
        base = n["_world"] if "_world" in () else None  # placeholder
        return n, wq

    world = {}

    def walk(n, parent_pos, parent_q):
        local_q = parent_q
        wp = (
            parent_pos[0] + qrot(local_q, n["pos"])[0],
            parent_pos[1] + qrot(local_q, n["pos"])[1],
            parent_pos[2] + qrot(local_q, n["pos"])[2],
        )
        wq = qmul(parent_q, n["rot"])
        world[n["id"]] = (wp, wq, n)
        for c in n["children"]:
            walk(c, wp, wq)

    for r in roots:
        walk(r, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0))

    return order, roots, world


def subtree_flags(n):
    flags = {"gate": False, "trex": False, "bridge": False}
    stack = [n]
    while stack:
        cur = stack.pop()
        blob = " ".join([cur["prefab"], cur["geometry"], cur["material"]]).lower()
        cls = cur["entity_class"].lower()
        if "poort" in blob or "deur" in blob or cls == "door":
            flags["gate"] = True
        if "trexpaddock" in blob:
            flags["trex"] = True
        if "/bridges/" in blob:
            flags["bridge"] = True
        stack.extend(cur["children"])
    return flags


markers = []
counts = {}


def add(cat, label, cry_xyz):
    ux = OFFSET_CM - cry_xyz[0] * 100.0
    uy = OFFSET_CM - cry_xyz[1] * 100.0
    uz = cry_xyz[2] * 100.0
    markers.append({"cat": cat, "label": label, "x": ux, "y": uy, "z": uz})
    counts[cat] = counts.get(cat, 0) + 1


def safe(s):
    return "".join(ch for ch in s if ch.isalnum() or ch in "_-").strip("_") or "X"


# --- Roads: every Type="Road" anywhere ---
road_count = 0
for fn in os.listdir(LAYERS):
    if not fn.endswith(".lyr"):
        continue
    order, roots, world = load_layer(os.path.join(LAYERS, fn))
    layer_base = fn[:-4]

    for n in order:
        if n["type"] == "Road":
            wp, _, _ = world[n["id"]]
            add("Roads", "ROAD_" + safe(n["name"] or ("Trail%d" % (road_count + 1))), wp)
            road_count += 1

    if layer_base == "Entities":
        for n in order:
            if n["entity_class"].lower() == "spawnpoint":
                wp, _, _ = world[n["id"]]
                add("Arrival", "SPAWN_" + safe(n["name"] or "Spawn"), wp)

    if layer_base == "Voertuigen":
        idx = 0
        for r in roots:
            idx += 1
            wp, _, _ = world[r["id"]]
            add("Vehicles", "JEEP_" + safe(r["name"] or ("Node%d" % idx)), wp)

    if layer_base == "Hekken":
        bridge_idx = 0
        for n in order:
            if "/bridges/" in (n["geometry"] or "").lower():
                bridge_idx += 1
                wp, _, _ = world[n["id"]]
                add("Bridge", "BRIDGE_%s_%d" % (safe(n["name"]), bridge_idx), wp)
        for r in roots:
            f = subtree_flags(r)
            wp, _, _ = world[r["id"]]
            nm = safe(r["name"] or "FenceNode")
            if f["bridge"]:
                continue
            if f["gate"]:
                add("Gates", "GATE_" + nm, wp)
            elif f["trex"]:
                add("TrexPaddock", "TREXPAD_" + nm, wp)
            else:
                add("Fences", "FENCE_" + nm, wp)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as fh:
    json.dump(markers, fh)

print("COUNTS:", json.dumps(counts, sort_keys=True))
print("TOTAL:", len(markers))
xs = [m["x"] for m in markers]
ys = [m["y"] for m in markers]
zs = [m["z"] for m in markers]
print("X range: %.1f .. %.1f" % (min(xs), max(xs)))
print("Y range: %.1f .. %.1f" % (min(ys), max(ys)))
print("Z range: %.1f .. %.1f" % (min(zs), max(zs)))
