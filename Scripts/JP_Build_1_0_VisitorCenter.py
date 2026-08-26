import math
import os
import struct
import unreal
import zlib

# Visitor Center facade pass. It uses original placeholder geometry only; do
# not add film logos, the entrance relief, or other extracted movie artwork.

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assets = unreal.EditorAssetLibrary
project_dir = unreal.Paths.project_dir()
heightmap_path = os.path.join(
    project_dir, "Content", "JPBlockout", "JP_Island_Heightmap_2017_v05.png"
)


def read_heightmap(path):
    with open(path, "rb") as source:
        data = source.read()

    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("Expected a PNG heightmap: " + path)

    position = 8
    compressed = bytearray()
    width = height = None
    while position < len(data):
        length = struct.unpack(">I", data[position:position + 4])[0]
        chunk_type = data[position + 4:position + 8]
        chunk = data[position + 8:position + 8 + length]
        position += length + 12
        if chunk_type == b"IHDR":
            width, height, depth, color, _, _, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
            if depth != 16 or color != 0 or interlace != 0:
                raise RuntimeError("Expected a non-interlaced 16-bit grayscale heightmap.")
        elif chunk_type == b"IDAT":
            compressed.extend(chunk)
        elif chunk_type == b"IEND":
            break

    raw = zlib.decompress(bytes(compressed))
    stride = width * 2
    previous = bytearray(stride)
    rows = []
    position = 0

    def paeth(a, b, c):
        estimate = a + b - c
        distances = (abs(estimate - a), abs(estimate - b), abs(estimate - c))
        return a if distances[0] <= distances[1] and distances[0] <= distances[2] else (
            b if distances[1] <= distances[2] else c
        )

    for _ in range(height):
        filter_type = raw[position]
        position += 1
        scanline = bytearray(raw[position:position + stride])
        position += stride
        reconstructed = bytearray(stride)
        for index in range(stride):
            left = reconstructed[index - 2] if index >= 2 else 0
            up = previous[index]
            upper_left = previous[index - 2] if index >= 2 else 0
            value = scanline[index]
            if filter_type == 1:
                value = (value + left) & 255
            elif filter_type == 2:
                value = (value + up) & 255
            elif filter_type == 3:
                value = (value + (left + up) // 2) & 255
            elif filter_type == 4:
                value = (value + paeth(left, up, upper_left)) & 255
            elif filter_type != 0:
                raise RuntimeError("Unsupported PNG filter.")
            reconstructed[index] = value
        rows.append([(reconstructed[i] << 8) | reconstructed[i + 1] for i in range(0, stride, 2)])
        previous = reconstructed
    return width, height, rows


if not os.path.exists(heightmap_path):
    raise RuntimeError("Missing heightmap: " + heightmap_path)

map_width, map_height, height_samples = read_heightmap(heightmap_path)


def terrain_z(x, y):
    sample_x = max(0.0, min(map_width - 1.001, (x + 100800.0) / 100.0))
    sample_y = max(0.0, min(map_height - 1.001, (y + 100800.0) / 100.0))
    x0, y0 = int(sample_x), int(sample_y)
    x1, y1 = min(map_width - 1, x0 + 1), min(map_height - 1, y0 + 1)
    tx, ty = sample_x - x0, sample_y - y0
    value = (
        height_samples[y0][x0] * (1.0 - tx) * (1.0 - ty)
        + height_samples[y0][x1] * tx * (1.0 - ty)
        + height_samples[y1][x0] * (1.0 - tx) * ty
        + height_samples[y1][x1] * tx * ty
    )
    return (float(value) - 32768.0) * 100.0 / 128.0


cube = assets.load_asset("/Engine/BasicShapes/Cube.Cube")
cylinder = assets.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
cone = assets.load_asset("/Engine/BasicShapes/Cone.Cone")
if not all((cube, cylinder, cone)):
    raise RuntimeError("Could not load Unreal basic shape meshes.")


def material(name):
    path = "/Game/JPGenerated/Materials/" + name
    if not assets.does_asset_exist(path):
        raise RuntimeError("Missing generated material: " + path)
    return assets.load_asset(path)


stone = material("M_JP_Stone")
concrete = material("M_JP_Concrete")
dark = material("M_JP_GateDark")
roof = material("M_JP_RoofRed")
grass = material("M_JP_Grass")
leaf = material("M_JP_Leaf")
trunk = material("M_JP_Trunk")


def previous_build_actors():
    return [
        actor for actor in actors.get_all_level_actors()
        if actor.get_actor_label().startswith("B10_JP_VC_")
    ]


for actor in previous_build_actors():
    actors.destroy_actor(actor)

# Keep all previous construction passes available, but prevent their simplified
# Visitor Center massing from overlapping this replacement pass.
for actor in actors.get_all_level_actors():
    label = actor.get_actor_label()
    if label.startswith(("B08_JP_VC_", "B09_JP_VC_", "B11_JP_VC_")):
        actor.set_is_temporarily_hidden_in_editor(True)


def spawn(label, mesh, x, y, z, sx, sy, sz, surface, yaw=0.0):
    actor = actors.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(x, y, z), unreal.Rotator(0.0, yaw, 0.0)
    )
    actor.set_actor_label("B10_JP_VC_" + label)
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_material(0, surface)
    actor.set_actor_scale3d(unreal.Vector(sx, sy, sz))
    return actor


def grounded(label, mesh, x, y, sx, sy, sz, surface, extra=0.0, yaw=0.0):
    return spawn(label, mesh, x, y, terrain_z(x, y) + sz * 50.0 + extra, sx, sy, sz, surface, yaw)


# The facade faces -X, toward the forecourt. Dimensions are in Unreal cm.
cx, cy = -10080.0, -3024.0
ground_z = terrain_z(cx, cy)

# Foundation and symmetric landscaped approach.
grounded("Plinth", cylinder, cx, cy, 37.0, 37.0, 0.35, stone, 16.0)
grounded("Forecourt", cylinder, cx - 5700.0, cy, 23.0, 23.0, 0.12, concrete, 20.0)
grounded("ArrivalDrive", cube, cx - 8600.0, cy, 43.0, 9.0, 0.10, dark, 15.0)

# Low wing volumes form a broad, concave arrival silhouette. The cylindrical
# wall sections avoid the rectangular-block look of the older pass.
for side in (-1.0, 1.0):
    wing_y = cy + side * 2350.0
    grounded("WingBase_%s" % int(side), cylinder, cx + 350.0, wing_y, 16.0, 13.0, 2.6, concrete, 20.0)
    grounded("WingRoof_%s" % int(side), cone, cx + 350.0, wing_y, 18.0, 15.0, 2.1, roof, 410.0)
    grounded("WingEave_%s" % int(side), cylinder, cx + 350.0, wing_y, 18.5, 15.5, 0.20, dark, 390.0)
    # Three dark glazed bays read as deep openings without relying on assets.
    for bay in (-600.0, 0.0, 600.0):
        spawn("WingWindow_%s_%s" % (int(side), int(bay)), cube,
              cx - 1160.0, wing_y + bay, terrain_z(cx - 1160.0, wing_y + bay) + 300.0,
              0.12, 2.2, 3.2, dark, 0.0)

# Main hall, high central roof, and a clerestory ring.
grounded("MainHall", cylinder, cx + 400.0, cy, 21.5, 21.5, 4.4, concrete, 24.0)
spawn("MainRoof", cone, cx + 400.0, cy, ground_z + 1120.0, 24.0, 24.0, 4.3, roof)
spawn("MainEave", cylinder, cx + 400.0, cy, ground_z + 860.0, 24.5, 24.5, 0.22, dark)
spawn("Clerestory", cylinder, cx + 400.0, cy, ground_z + 1350.0, 8.0, 8.0, 1.1, dark)
spawn("ClerestoryRoof", cone, cx + 400.0, cy, ground_z + 1570.0, 9.5, 9.5, 1.8, roof)

# Entry pavilion: a deep dark door, a stone surround, and an original abstract
# panel proportioned for later replacement with commissioned artwork.
grounded("EntryBlock", cube, cx - 2420.0, cy, 7.5, 12.0, 4.3, concrete, 20.0)
spawn("EntryDoor", cube, cx - 2800.0, cy, terrain_z(cx - 2800.0, cy) + 310.0, 0.18, 5.4, 4.7, dark)
spawn("EntryPanel", cube, cx - 2825.0, cy, terrain_z(cx - 2825.0, cy) + 650.0, 0.12, 6.5, 1.4, stone)
spawn("EntryLintel", cube, cx - 2780.0, cy, terrain_z(cx - 2780.0, cy) + 830.0, 1.1, 13.0, 0.8, stone)

# Columned portico across the front facade. Each column gets a base and cap so
# the assembly reads as a finished arrival building rather than a graybox.
for index, offset in enumerate((-1550.0, -1050.0, -525.0, 525.0, 1050.0, 1550.0)):
    x = cx - 2730.0
    y = cy + offset
    z = terrain_z(x, y)
    spawn("ColumnBase_%02d" % index, cylinder, x, y, z + 55.0, 0.78, 0.78, 0.22, stone)
    spawn("Column_%02d" % index, cylinder, x, y, z + 370.0, 0.55, 0.55, 6.1, stone)
    spawn("ColumnCap_%02d" % index, cylinder, x, y, z + 685.0, 0.75, 0.75, 0.22, stone)

# Wide stairs and terraced planters create the characteristic stepped approach.
for step in range(7):
    x = cx - 3950.0 + step * 170.0
    grounded("EntryStep_%02d" % step, cube, x, cy, 4.8 - step * 0.35, 13.5, 0.22, stone, 18.0)

for side in (-1.0, 1.0):
    for tier in range(3):
        x = cx - 3900.0 + tier * 460.0
        y = cy + side * (1850.0 - tier * 260.0)
        grounded("Planter_%s_%s" % (int(side), tier), cube, x, y, 6.0, 3.0, 0.65, concrete, 30.0)
        for plant in range(4):
            px = x - 360.0 + plant * 240.0
            py = y + side * 40.0
            pz = terrain_z(px, py)
            spawn("PlantTrunk_%s_%s_%s" % (int(side), tier, plant), cylinder,
                  px, py, pz + 95.0, 0.12, 0.12, 1.9, trunk)
            spawn("PlantLeaf_%s_%s_%s" % (int(side), tier, plant), cone,
                  px, py, pz + 255.0, 1.2, 1.2, 1.1, leaf, plant * 45.0)

# Exterior colonnade and window rhythm across both wings.
for side in (-1.0, 1.0):
    for index in range(5):
        y = cy + side * (450.0 + index * 690.0)
        x = cx - 1180.0 + index * 270.0
        z = terrain_z(x, y)
        spawn("WingColumn_%s_%02d" % (int(side), index), cylinder,
              x, y, z + 320.0, 0.38, 0.38, 5.6, stone)

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    unreal.EditorLevelLibrary.save_current_level()

unreal.log("JP BUILD 1.0 COMPLETE: Visitor Center facade created; actors=%d" % len(previous_build_actors()))
