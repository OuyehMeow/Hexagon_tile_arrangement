# AGENTS.md — Repository Architecture Invariant

This repository follows **Method in the Cloud, Data at Local**:

- **GitHub (this repo) = Method only:** HTML/JS apps, Python scripts, Docker/NAS deployment templates, tests, and docs. Never commit generated SVGs, DXFs, CSVs, OBJ tile sets, `.env`, or local paths.
- **External `DATA_ROOT` = Data only:** All generated outputs live strictly outside this repo under a user-configured `DATA_ROOT` (Google Drive synced folder today, or a mounted volume on a home NAS):
  ```
  <DATA_ROOT>/
  └── exports/
      ├── <YYYY-MM-DD>_<cols>x<rows>_seed<seed>/
      │   ├── hex_paths.svg
      │   ├── layout.svg
      │   ├── config.json
      │   ├── tiles.csv          (Save all)
      │   └── hex_tiles.dxf      (Save all)
      └── tile_sets/             (from make_hex_tiles.py)
  ```

## `DATA_ROOT` Resolution Precedence
1. Explicit CLI flag (`--data-dir`)
2. Environment variable (`HEX_DATA_DIR`)
3. User-local config (`~/.config/hex-path-tiles/config.json` -> `{"data_dir": "..."}`)
4. Local fallback (`./data`, git-ignored)

## Key Design Decisions
- Flat-top hexagon, $R = 55\text{ mm}$, edges 1–6 CCW from upper-right.
- Exports are 1:1 mm, never overwrite existing folders (suffix `_2`, `_3`, ...).
- `hex-path-composer.html` must remain functional both standalone (opened directly in Chrome/Edge) and when served by `server.py` (local PC or home NAS).
