# Hex Path Tiles

Hexagon tiles (flat-top, R = 55 mm) whose paths join edge midpoints, and a composer that arranges them
on a board and exports cut-ready, 1:1 mm drawings.

| File | What it does |
|---|---|
| `hex-path-composer.html` | The composer: layout → linetype → line parameters → output. |
| `hex-path-tiles.html` | 3D viewer of every tile combination (1 path, 3 paths, 3–6 edges). |
| `make_hex_tiles.py` | Writes those tile sets as DXF (true arcs), OBJ and CSV. |

No install and no server: open the HTML files in Chrome or Edge. Fonts and three.js load from CDNs.

## Use

Double-click `hex-path-composer.html`. In **Output**, Export SVG asks once for a folder (the browser
remembers it; **Choose folder** changes it). Each press then creates
`<folder>/<date>_<cols>x<rows>_seed<seed>/` (`_2`, `_3` … when the name is taken) with `hex_paths.svg`,
`layout.svg` and `config.json`; Save all adds `tiles.csv` and `hex_tiles.dxf`.

Browsers forbid folder pickers inside a cross-origin frame (the claude.ai artifact viewer, the Claude
desktop preview), and Firefox and Safari have no folder access. There the same folder is saved as one
`<date>_<cols>x<rows>_seed<seed>.zip` instead (through the viewer's save prompt when embedded).

```bash
python make_hex_tiles.py <output folder>   # tile sets; default ./exports/tile_sets (git-ignored)
```

## Method

**Geometry.** Edge k (0-based, CCW from the upper-right edge) has its midpoint at angle 30° + 60k, distance
A = R√3/2. A path between two edges is the circular arc that meets both edges at 90°: its centre is where
the two edge lines cross. Adjacent edges: r 27.5, 120°. Skip one: r 82.5, 60°. Opposite: straight, 95.26.

**Tile sets.** The 15 possible lines are bits of a mask. For k edges, every connected line set whose ends
are exactly those edges is kept once per rotation/reflection class (12 symmetries, minimum mask is
canonical): 9, 64, 384 and 2455 tiles for k = 3…6. IDs `kE-0001` are sorted by line count, then mask.

**Layout.** Offset-column grid, centre (1.5R·col, −(2A·row + A·(col mod 2))). Each lit tile draws a number
2…6 (edges carrying a path). A shared edge is used by both tiles or neither; with open ends on, an edge
facing an empty cell may end a path. A seeded random walk repairs degree mismatches (re-drawing numbers
that cannot be met), then each tile takes a random connected line set on its path edges.

**Linetypes.**
- *Single*: the path itself.
- *Offset*: concentric arcs / parallel lines at ±d. Gaps come from a cubic Bezier graph mapper:
  x_i evenly spaced 0…1, y_i = B(x_i), gap_i = g0 + y_i (g1 − g0), d_k = Σ gap. Every copy lands at
  midpoint ± d on the edge, so copies continue into the neighbour. Copies beyond R/2 are dropped.
- *Spiral*: a coil around the path, offset = a·ρ(φ)·[cos φ·sin α·T + sin φ·N]; ρ blends a polygon section
  into a circle, α tilts the section from an edge-on swing (0°) to the full section (90°). φ = ∫ω, with
  ω = ω0·4^(v·n(s)) and n smooth noise, giving loose and dense stretches. At shared edges every coil
  arrives at φ = ±90° and the same noise value, so coils join; open ends shrink to the midpoint.

All randomness is seeded (mulberry32); `config.json` records every parameter needed to rebuild an export.
