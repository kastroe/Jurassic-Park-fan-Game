import unreal
import os
import struct
import zlib

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# ------------------------------------------------------------
# DIRECT HEIGHTMAP READER
# ------------------------------------------------------------
# We bypass UE 5.8's broken Python HitResult bindings entirely and read the
# original 16-bit grayscale PNG heightmap that created this landscape.

project_dir = unreal.Paths.project_dir()
png_path = os.path.join(
    project_dir, "Content", "JPBlockout", "JP_Island_Heightmap_2017.png"
)

if not os.path.exists(png_path):
    raise RuntimeError(
        "Heightmap PNG not found at: " + png_path +
        "\nCopy JP_Island_Heightmap_2017.png back into Content/JPBlockout."
    )

def read_png16_gray(path):
    with open(path, "rb") as f:
        data = f.read()

    sig = b"\x89PNG\r\n\x1a\n"
    if data[:8] != sig:
        raise RuntimeError("Heightmap is not a PNG file.")

    pos = 8
    width = height = None
    bit_depth = color_type = None
    idat = bytearray()

    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos+4])[0]
        ctype = data[pos+4:pos+8]
        chunk = data[pos+8:pos+8+length]
        pos += 12 + length

        if ctype == b"IHDR":
            width, height, bit_depth, color_type, comp, filt, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
            if bit_depth != 16 or color_type != 0:
                raise RuntimeError(
                    "Expected 16-bit grayscale PNG; got bit_depth=%s color_type=%s"
                    % (bit_depth, color_type)
                )
            if interlace != 0:
                raise RuntimeError("Interlaced PNG is not supported by this script.")
        elif ctype == b"IDAT":
            idat.extend(chunk)
        elif ctype == b"IEND":
            break

    raw = zlib.decompress(bytes(idat))
    bpp = 2
    stride = width * bpp
    rows = []
    prev = bytearray(stride)
    p = 0

    def paeth(a, b, c):
        pp = a + b - c
        pa = abs(pp - a)
        pb = abs(pp - b)
        pc = abs(pp - c)
        if pa <= pb and pa <= pc:
            return a
        if pb <= pc:
            return b
        return c

    for _y in range(height):
        ftype = raw[p]
        p += 1
        scan = bytearray(raw[p:p+stride])
        p += stride

        recon = bytearray(stride)
        for i in range(stride):
            x = scan[i]
            a = recon[i-bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i-bpp] if i >= bpp else 0

            if ftype == 0:
                val = x
            elif ftype == 1:
                val = (x + a) & 255
            elif ftype == 2:
                val = (x + b) & 255
            elif ftype == 3:
                val = (x + ((a + b) // 2)) & 255
            elif ftype == 4:
                val = (x + paeth(a, b, c)) & 255
            else:
                raise RuntimeError("Unsupported PNG filter type: %d" % ftype)

            recon[i] = val

        row = []
        for i in range(0, stride, 2):
            row.append((recon[i] << 8) | recon[i+1])

        rows.append(row)
        prev = recon

    return width, height, rows

W, H, HM = read_png16_gray(png_path)

if W != 2017 or H != 2017:
    unreal.log_warning("Unexpected heightmap size: %dx%d" % (W, H))

# ------------------------------------------------------------
# LANDSCAPE MAPPING
# ------------------------------------------------------------
# The map was imported as 2017x2017 at XY scale 100.
# A 2017 landscape contains 2016 intervals => 201600 cm across.
# The import gizmo shown in the editor was -100800,-100800.
WORLD_MIN_X = -100800.0
WORLD_MIN_Y = -100800.0
XY_PER_PIXEL = 100.0

# Default landscape Z scale is 100.
# Unreal's 16-bit landscape mapping is:
# world Z cm = (height16 - 32768) * ZScale / 128.
LANDSCAPE_Z_SCALE = 100.0
LANDSCAPE_ACTOR_Z = 0.0

def height16_to_world_z(v):
    return LANDSCAPE_ACTOR_Z + (float(v) - 32768.0) * LANDSCAPE_Z_SCALE / 128.0

def height_at_world(x, y):
    fx = (x - WORLD_MIN_X) / XY_PER_PIXEL
    fy = (y - WORLD_MIN_Y) / XY_PER_PIXEL

    # Clamp to landscape.
    fx = max(0.0, min(W - 1.001, fx))
    fy = max(0.0, min(H - 1.001, fy))

    x0 = int(fx)
    y0 = int(fy)
    x1 = min(W - 1, x0 + 1)
    y1 = min(H - 1, y0 + 1)
    tx = fx - x0
    ty = fy - y0

    h00 = HM[y0][x0]
    h10 = HM[y0][x1]
    h01 = HM[y1][x0]
    h11 = HM[y1][x1]

    h0 = h00 * (1.0 - tx) + h10 * tx
    h1 = h01 * (1.0 - tx) + h11 * tx
    hv = h0 * (1.0 - ty) + h1 * ty
    return height16_to_world_z(hv)

# ------------------------------------------------------------
# ACTOR HELPERS
# ------------------------------------------------------------

def by_prefix(prefix):
    return [a for a in actor_sub.get_all_level_actors()
            if a.get_actor_label().startswith(prefix)]

def by_label(label):
    for a in actor_sub.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None

def actor_half_height(actor):
    try:
        _origin, extent = actor.get_actor_bounds(False)
        return max(5.0, float(extent.z))
    except Exception:
        return 5.0

def place_on_ground(actor, extra=5.0):
    p = actor.get_actor_location()
    z = height_at_world(p.x, p.y)
    actor.set_actor_location(
        unreal.Vector(p.x, p.y, z + actor_half_height(actor) + extra),
        False,
        False
    )

moved = 0

# Roads
roads = [
    a for a in actor_sub.get_all_level_actors()
    if a.get_actor_label().startswith("GB_JP_ARRIVAL_")
    or a.get_actor_label().startswith("GB_JP_TOUR_")
]

for a in roads:
    place_on_ground(a, 3.0)
    moved += 1

# Paddock pads
for a in by_prefix("GB_JP_ZONE_"):
    place_on_ground(a, 3.0)
    moved += 1

# Main structures
for label in [
    "GB_JP_Helipad",
    "GB_JP_VisitorCenter_Main",
    "GB_JP_VisitorCenter_Rotunda",
    "GB_JP_RaptorPen",
    "GB_JP_TourGate_L",
    "GB_JP_TourGate_R",
    "GB_JP_Maintenance",
    "GB_JP_PlayerStart",
]:
    a = by_label(label)
    if a:
        place_on_ground(a, 8.0)
        moved += 1

# Tour gate overhead beam after pillars are grounded.
left = by_label("GB_JP_TourGate_L")
right = by_label("GB_JP_TourGate_R")
top = by_label("GB_JP_TourGate_Top")

if left and right and top:
    lp = left.get_actor_location()
    rp = right.get_actor_location()
    _, le = left.get_actor_bounds(False)
    _, re = right.get_actor_bounds(False)
    _, te = top.get_actor_bounds(False)

    pillar_top = max(lp.z + le.z, rp.z + re.z)
    tp = top.get_actor_location()
    top.set_actor_location(
        unreal.Vector(tp.x, tp.y, pillar_top + te.z + 10.0),
        False, False
    )
    moved += 1

# Rebuild ground beacons using the heightmap directly.
for a in list(by_prefix("FIT_JP_BEACON_")):
    actor_sub.destroy_actor(a)

cyl = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
if cyl:
    for marker in by_prefix("AUTO_JP_"):
        p = marker.get_actor_location()
        z = height_at_world(p.x, p.y)

        beacon = actor_sub.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(p.x, p.y, z + 125.0),
            unreal.Rotator()
        )
        beacon.set_actor_label(
            "FIT_JP_BEACON_" + marker.get_actor_label().replace("AUTO_JP_", "")
        )
        beacon.static_mesh_component.set_static_mesh(cyl)
        beacon.set_actor_scale3d(unreal.Vector(2.0, 2.0, 2.5))

# Hide original floating landmark references.
for marker in by_prefix("AUTO_JP_"):
    try:
        marker.set_is_temporarily_hidden_in_editor(True)
    except Exception:
        pass

# Save.
try:
    level_sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    level_sub.save_current_level()
except Exception:
    unreal.EditorLevelLibrary.save_current_level()

unreal.log("JP BUILD 0.4.4 COMPLETE: moved=%d using DIRECT HEIGHTMAP DATA" % moved)
