"""Generate hexagon path tiles (R = 55 mm) as DXF (true arcs) and OBJ (polylines).

Edge n (1..6) is numbered CCW starting at the upper-right edge of a flat-top hexagon.
Each path joins two edge midpoints with a circular arc that meets both edges at 90 degrees
(centre = intersection of the two edge lines); opposite edges get a straight line.

Outputs:
  hex_tiles_single.dxf / .obj  - 15 tiles, one path each (every pair of edges)
  hex_tiles_triple.dxf / .obj  - 15 tiles, three paths each (every pairing of all six edges)
  hex_tiles_3edges.dxf / .obj / .csv ... hex_tiles_6edges.*
      every connected set of lines joining exactly k edge midpoints (k-1 up to k(k-1)/2 lines),
      one tile per rotation/reflection class: 9, 64, 384 and 2455 tiles.
      Tile IDs (e.g. 4E-0012) match the 3D viewer; the CSV lists each tile's lines.

Usage: python make_hex_tiles.py [output folder]   (default: ./exports/tile_sets beside this script)
"""
import math
import os
import sys

R = 55.0
GAP = 8.0
A = R * math.sqrt(3) / 2
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports", "tile_sets")
KIND = {1: "PATH_ADJ", 2: "PATH_SKIP", 3: "PATH_OPP"}
COLOR = {"HEX": 8, "PATH_ADJ": 4, "PATH_SKIP": 30, "PATH_OPP": 5, "LABEL": 7}


def mid(k):
    t = math.radians(30 + 60 * k)
    return (A * math.cos(t), A * math.sin(t))


def edge_dir(k):
    t = math.radians(120 + 60 * k)
    return (math.cos(t), math.sin(t))


def path_geom(i, j):
    P, Q, d1, d2 = mid(i), mid(j), edge_dir(i), edge_dir(j)
    kind = min(abs(i - j), 6 - abs(i - j))
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return {"kind": kind, "line": (P, Q), "pts": [P, Q]}
    t = ((Q[0] - P[0]) * d2[1] - (Q[1] - P[1]) * d2[0]) / den
    C = (P[0] + t * d1[0], P[1] + t * d1[1])
    r = math.hypot(P[0] - C[0], P[1] - C[1])
    a1 = math.atan2(P[1] - C[1], P[0] - C[0])
    s = math.atan2(Q[1] - C[1], Q[0] - C[0]) - a1
    s = (s + math.pi) % (2 * math.pi) - math.pi
    pts = [(C[0] + r * math.cos(a1 + s * n / 48), C[1] + r * math.sin(a1 + s * n / 48)) for n in range(49)]
    return {"kind": kind, "arc": (C, r, a1, s), "pts": pts}


def matchings(items):
    if not items:
        return [[]]
    a, rest = items[0], items[1:]
    out = []
    for idx, b in enumerate(rest):
        for m in matchings(rest[:idx] + rest[idx + 1:]):
            out.append([(a, b)] + m)
    return out


PAIRS = [(i, j) for i in range(6) for j in range(i + 1, 6)]
SYMS = [[PAIRS.index(tuple(sorted(((f * i + r) % 6, (f * j + r) % 6)))) for i, j in PAIRS]
        for r in range(6) for f in (1, -1)]


def connected_sets(k):
    """Connected line sets touching exactly k edges; one per rotation/reflection class, same order as the viewer."""
    out = []
    for m in range(1, 1 << 15):
        ps = [PAIRS[b] for b in range(15) if m >> b & 1]
        verts = {v for p in ps for v in p}
        if len(verts) != k:
            continue
        seen, grew = {ps[0][0]}, True
        while grew:
            grew = False
            for i, j in ps:
                if (i in seen) != (j in seen):
                    seen |= {i, j}
                    grew = True
        if seen != verts:
            continue
        if all(sum(1 << s[b] for b in range(15) if m >> b & 1) >= m for s in SYMS):
            out.append(m)
    out.sort(key=lambda m: (bin(m).count("1"), m))
    return [[PAIRS[b] for b in range(15) if m >> b & 1] for m in out]


def centres(count, gap):
    D = 2 * A + gap
    cols = 5 if count <= 15 else math.ceil(math.sqrt(count * 1.6))
    pts = [((n % cols) * D * math.sqrt(3) / 2, -((n // cols) * D + (n % cols % 2) * D / 2)) for n in range(count)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    return [(x - cx, y - cy) for x, y in pts]


def label(pairs):
    return " ".join(f"{i + 1}-{j + 1}" for i, j in pairs)


def tile_names(name, tiles):
    if name[0].isdigit():
        return [f"{name[0]}E-{n:04d}" if len(t) > 3 else label(t) for n, t in enumerate(tiles, 1)]
    return [label(t) for t in tiles]


def write_dxf(path, tiles, names):
    out = ["0", "SECTION", "2", "ENTITIES"]

    def ent(*kv):
        out.extend(str(x) for x in kv)

    f = lambda x: f"{x:.4f}"
    for (cx, cy), pairs, name in zip(centres(len(tiles), GAP), tiles, names):
        for k in range(6):
            a, b = math.radians(60 * k), math.radians(60 * (k + 1))
            ent("0", "LINE", "8", "HEX", "62", COLOR["HEX"],
                "10", f(cx + R * math.cos(a)), "20", f(cy + R * math.sin(a)), "30", "0",
                "11", f(cx + R * math.cos(b)), "21", f(cy + R * math.sin(b)), "31", "0")
        for i, j in pairs:
            g = path_geom(i, j)
            layer = KIND[g["kind"]]
            if "line" in g:
                (x1, y1), (x2, y2) = g["line"]
                ent("0", "LINE", "8", layer, "62", COLOR[layer],
                    "10", f(cx + x1), "20", f(cy + y1), "30", "0", "11", f(cx + x2), "21", f(cy + y2), "31", "0")
            else:
                C, r, a1, s = g["arc"]
                st, en = (a1, a1 + s) if s > 0 else (a1 + s, a1)
                ent("0", "ARC", "8", layer, "62", COLOR[layer], "10", f(cx + C[0]), "20", f(cy + C[1]), "30", "0",
                    "40", f(r), "50", f(math.degrees(st) % 360), "51", f(math.degrees(en) % 360))
        ent("0", "TEXT", "8", "LABEL", "62", COLOR["LABEL"], "10", f(cx), "20", f(cy - A - 10), "30", "0",
            "40", "5", "1", name, "72", "1", "11", f(cx), "21", f(cy - A - 10), "31", "0")
    out += ["0", "ENDSEC", "0", "EOF"]
    with open(path, "w", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")


def write_obj(path, tiles, names):
    lines = ["# Hex path tiles, R=55mm, units mm, Z up"]
    vi = 0
    for n, ((cx, cy), pairs, name) in enumerate(zip(centres(len(tiles), GAP), tiles, names), 1):
        lines.append(f"o tile_{n}_{label(pairs).replace('-', '').replace(' ', '_')}")
        for k in range(6):
            t = math.radians(60 * k)
            lines.append(f"v {cx + R * math.cos(t):.4f} {cy + R * math.sin(t):.4f} 0")
        lines.append("l " + " ".join(str(vi + k) for k in [1, 2, 3, 4, 5, 6, 1]))
        vi += 6
        for i, j in pairs:
            pts = path_geom(i, j)["pts"]
            lines += [f"v {cx + x:.4f} {cy + y:.4f} 0" for x, y in pts]
            lines.append("l " + " ".join(str(vi + k + 1) for k in range(len(pts))))
            vi += len(pts)
    with open(path, "w", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    single = [[(i, j)] for i in range(6) for j in range(i + 1, 6)]
    triple = matchings(list(range(6)))
    sets = [("single", single), ("triple", triple)] + [(f"{k}edges", connected_sets(k)) for k in (3, 4, 5, 6)]
    os.makedirs(OUT, exist_ok=True)
    for name, tiles in sets:
        names = tile_names(name, tiles)
        write_dxf(os.path.join(OUT, f"hex_tiles_{name}.dxf"), tiles, names)
        write_obj(os.path.join(OUT, f"hex_tiles_{name}.obj"), tiles, names)
        if name[0].isdigit():
            with open(os.path.join(OUT, f"hex_tiles_{name}.csv"), "w", newline="\n") as fh:
                fh.write("tile,lines,connections\n")
                fh.writelines(f"{name[0]}E-{n:04d},{len(t)},{label(t)}\n" for n, t in enumerate(tiles, 1))
        print(name, len(tiles), "tiles")
