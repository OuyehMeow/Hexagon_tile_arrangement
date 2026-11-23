# Hex Path Tiles

Hexagon tiles (flat-top, R = 55 mm) whose paths join edge midpoints, and a composer that arranges them
on a board and exports cut-ready, 1:1 mm drawings for a pen plotter.

| File | What it does |
|---|---|
| `hex-path-composer.html` | The composer: layout → linetype → line parameters → output. |
| `hex-path-tiles.html` | 3D viewer of every tile combination (1 path, 3 paths, 3–6 edges). |
| `make_hex_tiles.py` | Writes those tile sets as DXF (true arcs), OBJ and CSV. |
| `server.py` | Optional zero-dependency web server for local PC or home NAS hosting. |
| `Dockerfile` / `docker-compose.yml` | One-command container setup for a home NAS (Synology, TrueNAS, Unraid, Raspberry Pi). |

---

## Startup Guide

This project follows **Method in the Cloud, Data at Local**: code lives in GitHub, while all exports live outside the repo under a single `HEX_DATA_DIR` folder (your Google Drive folder today, or a NAS share later).

### Option A — Simplest on a PC (no install, no server)
1. Double-click `hex-path-composer.html` in **Chrome** or **Edge**.
2. Right-click / right-drag tiles on the board, click **Assign tiles**, and tune your linetype.
3. Click **Export SVG** (or **Save all**). The first time, pick your `exports/` folder (e.g. `G:\My Drive\...\HEXAGON_TILE_ARRANGEMENT\exports`). The browser remembers it.
4. Each press creates a new `<date>_<cols>x<rows>_seed<seed>/` subfolder (`_2`, `_3` … if taken) with `hex_paths.svg`, `layout.svg`, and `config.json` (plus `tiles.csv` and `hex_tiles.dxf` for **Save all**).

### Option B — Local Python server (any browser on your PC or LAN)
```bash
python3 server.py --data-dir "/path/to/HEXAGON_TILE_ARRANGEMENT"
```
- Open `http://127.0.0.1:8765/` for the composer, or `http://127.0.0.1:8765/tiles` for the 3D tile viewer.
- Add `--host 0.0.0.0` to open it from another device (e.g. iPad or laptop) on your Wi-Fi.
- Exports save directly into `<data-dir>/exports/` with no browser folder picker needed.

### Option C — Home NAS (Docker Compose, ready for future move)
1. Clone this repository onto your NAS:
   ```bash
   git clone https://github.com/OuyehMeow/Hexagon_tile_arrangement.git
   cd Hexagon_tile_arrangement
   ```
2. Copy the environment template and set your NAS data folder:
   ```bash
   cp .env.example .env
   # Edit .env and set HEX_DATA_DIR=/path/on/your/nas/HEXAGON_TILE_ARRANGEMENT
   ```
3. Start the container:
   ```bash
   docker compose up -d
   ```
4. Open `http://<your-nas-ip>:8765/` from any browser on your home network (and `/tiles` for the 3D viewer). Every export writes straight into `<HEX_DATA_DIR>/exports/<date>_<cols>x<rows>_seed<seed>/`.
5. To update later:
   ```bash
   git pull && docker compose up -d --build
   ```

### Generate the full tile catalog (optional)
```bash
python3 make_hex_tiles.py                    # writes to <HEX_DATA_DIR>/exports/tile_sets (or ./exports/tile_sets)
python3 make_hex_tiles.py /custom/tile_sets  # explicit output folder
```

---

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
