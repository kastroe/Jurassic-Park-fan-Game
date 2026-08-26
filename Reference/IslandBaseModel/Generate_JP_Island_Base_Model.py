"""Generate a closed, Unreal-scale island base mesh from the supplied map.

The mesh uses centimeters, Z-up, north at +Y, and contains only an approximate
coastline and broad terrain masses. It intentionally contains no map artwork,
logos, roads, buildings, or other reference-image overlays.
"""

from math import exp
from pathlib import Path
from struct import pack
from zlib import compress, crc32


OUTPUT = Path(__file__).with_name("SM_JP_Island_Base_2km.obj")
PREVIEW_OUTPUT = Path(__file__).with_name("SM_JP_Island_Base_2km_Preview.png")

# World dimensions in Unreal centimeters.
WIDTH_CM = 154000.0
LENGTH_CM = 200000.0
RELIEF_CM = 18000.0
SEA_FLOOR_CM = -2500.0
GRID_X = 129
GRID_Y = 165

# Normalized clockwise shoreline, traced from the supplied island map.
# North is +Y; the narrow southern peninsula is at the bottom of the image.
SHORELINE = (
    (-0.08, 1.00), (-0.38, 0.99), (-0.70, 0.91), (-0.89, 0.72),
    (-0.86, 0.48), (-0.77, 0.30), (-0.71, 0.10), (-0.68, -0.13),
    (-0.57, -0.35), (-0.48, -0.60), (-0.60, -0.78), (-0.45, -0.90),
    (-0.20, -0.97), (-0.08, -1.00), (0.03, -0.91), (0.11, -0.78),
    (0.23, -0.82), (0.35, -0.68), (0.43, -0.48), (0.49, -0.26),
    (0.45, -0.04), (0.53, 0.17), (0.82, 0.22), (0.91, 0.42),
    (0.82, 0.62), (0.91, 0.77), (0.72, 0.85), (0.54, 0.80),
    (0.41, 0.70), (0.28, 0.83), (0.12, 0.92),
)

# Broad mountain groups visible on the supplied map: northwest caldera,
# western ridge, northeast highland, eastern ridge, and southern volcano.
PEAKS = (
    (-0.48, 0.73, 0.96, 0.17),
    (-0.42, 0.32, 0.72, 0.16),
    (-0.56, 0.03, 0.46, 0.15),
    (0.20, 0.65, 0.63, 0.18),
    (0.63, 0.37, 0.58, 0.14),
    (0.50, 0.08, 0.40, 0.16),
    (-0.18, -0.58, 0.69, 0.17),
)


def is_inside(x, y):
    """Return whether normalized point x,y is within SHORELINE."""
    inside = False
    previous_x, previous_y = SHORELINE[-1]
    for current_x, current_y in SHORELINE:
        crosses = (current_y > y) != (previous_y > y)
        if crosses:
            crossing_x = (previous_x - current_x) * (y - current_y) / (previous_y - current_y) + current_x
            if x < crossing_x:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


def terrain_height(x, y):
    """Return terrain height in centimeters for normalized island coordinates."""
    height = 0.035
    for peak_x, peak_y, amplitude, radius in PEAKS:
        distance_squared = (x - peak_x) ** 2 + (y - peak_y) ** 2
        height += amplitude * exp(-distance_squared / (2.0 * radius ** 2))

    # Keep the map's central corridor usable for later park construction.
    height -= 0.18 * exp(-((x + 0.02) ** 2 / 0.08 + (y - 0.02) ** 2 / 0.85))
    return max(0.0, min(1.0, height)) * RELIEF_CM


def to_world(x, y):
    return x * WIDTH_CM * 0.5, y * LENGTH_CM * 0.5


def add_vertex(vertices, x, y, z):
    vertices.append((x, y, z))
    return len(vertices)


def write_preview():
    """Write a top-down terrain preview without requiring third-party packages."""
    width = 616
    height = 800
    rows = []
    for pixel_y in range(height):
        y = 1.0 - 2.0 * pixel_y / (height - 1)
        row = bytearray()
        for pixel_x in range(width):
            x = -1.0 + 2.0 * pixel_x / (width - 1)
            if not is_inside(x, y):
                # Deep-water background.
                row.extend((31, 91, 126))
                continue

            elevation = terrain_height(x, y) / RELIEF_CM
            # Lowlands are green; elevations transition through rock to peaks.
            if elevation < 0.22:
                blend = elevation / 0.22
                low = (49, 118, 48)
                high = (92, 145, 54)
            elif elevation < 0.58:
                blend = (elevation - 0.22) / 0.36
                low = (92, 145, 54)
                high = (58, 93, 46)
            else:
                blend = (elevation - 0.58) / 0.42
                low = (58, 93, 46)
                high = (126, 119, 87)
            row.extend(int(low[channel] + (high[channel] - low[channel]) * blend) for channel in range(3))
        rows.append(b"\x00" + bytes(row))

    def png_chunk(kind, data):
        return pack(">I", len(data)) + kind + data + pack(">I", crc32(kind + data) & 0xFFFFFFFF)

    png_data = b"\x89PNG\r\n\x1a\n"
    png_data += png_chunk(b"IHDR", pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png_data += png_chunk(b"IDAT", compress(b"".join(rows), 9))
    png_data += png_chunk(b"IEND", b"")
    PREVIEW_OUTPUT.write_bytes(png_data)


def generate():
    vertices = []
    top_vertices = {}
    bottom_vertices = {}

    for grid_y in range(GRID_Y):
        y = -1.0 + 2.0 * grid_y / (GRID_Y - 1)
        for grid_x in range(GRID_X):
            x = -1.0 + 2.0 * grid_x / (GRID_X - 1)
            if not is_inside(x, y):
                continue
            world_x, world_y = to_world(x, y)
            key = (grid_x, grid_y)
            top_vertices[key] = add_vertex(vertices, world_x, world_y, terrain_height(x, y))
            bottom_vertices[key] = add_vertex(vertices, world_x, world_y, SEA_FLOOR_CM)

    top_faces = []
    bottom_faces = []
    edge_counts = {}
    for grid_y in range(GRID_Y - 1):
        for grid_x in range(GRID_X - 1):
            southwest = (grid_x, grid_y)
            southeast = (grid_x + 1, grid_y)
            northeast = (grid_x + 1, grid_y + 1)
            northwest = (grid_x, grid_y + 1)
            corners = (southwest, southeast, northeast, northwest)
            if not all(corner in top_vertices for corner in corners):
                continue

            top_faces.append(tuple(top_vertices[corner] for corner in corners))
            bottom_faces.append(tuple(bottom_vertices[corner] for corner in reversed(corners)))
            for first, second in zip(corners, corners[1:] + corners[:1]):
                edge = tuple(sorted((first, second)))
                edge_counts[edge] = edge_counts.get(edge, 0) + 1

    side_faces = []
    for first, second in edge_counts:
        if edge_counts[(first, second)] != 1:
            continue
        side_faces.append((
            top_vertices[first], top_vertices[second],
            bottom_vertices[second], bottom_vertices[first],
        ))

    with OUTPUT.open("w", encoding="ascii", newline="\n") as obj_file:
        obj_file.write("# JP Island Base: 2 km x 1.54 km, centimeters, Z-up\n")
        obj_file.write("o SM_JP_Island_Base_2km\n")
        for x, y, z in vertices:
            obj_file.write("v %.3f %.3f %.3f\n" % (x, y, z))
        obj_file.write("g TerrainSurface\n")
        for face in top_faces:
            obj_file.write("f %d %d %d %d\n" % face)
        obj_file.write("g SeaFloor\n")
        for face in bottom_faces:
            obj_file.write("f %d %d %d %d\n" % face)
        obj_file.write("g CoastCliffs\n")
        for face in side_faces:
            obj_file.write("f %d %d %d %d\n" % face)

    print("Wrote %s" % OUTPUT)
    print("Vertices: %d; terrain quads: %d; coast quads: %d" % (
        len(vertices), len(top_faces), len(side_faces)
    ))
    write_preview()
    print("Wrote %s" % PREVIEW_OUTPUT)


if __name__ == "__main__":
    generate()
