# CLAUDE.md

## Project Overview
Python 3.14 toolkit for bundling Roam Research markdown exports with their
Firebase-hosted images into self-contained `.mdbundle` directories.

## Setup
```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

## Key Commands
```bash
bundle-roam-md -m <file> -p <port> -g <graph> -t <token> -o <output_dir>
pytest          # run tests
black .         # format code
pyright         # type check (strict)
```

## Project Structure
- `src/roam_pub/` — main package
  - `bundle_roam_md.py` — CLI entry point (Typer app)
  - `roam_md_bundle.py` — core bundling logic
  - `roam_asset.py` — Firebase asset fetching
  - `roam_model.py`, `roam_page.py`, `roam_transcribe.py` — in progress
- `tests/fixtures/` — sample markdown, images, JSON for tests

## Conventions
- Src layout: package lives under `src/roam_pub/`
- Line length: 120 chars (Black + Ruff)
- Docstrings: Google style (enforced by Ruff)
- Tests: pytest, files named `test_*.py`
- **Strong typing**: all Python code must use type annotations throughout; no `Any` types; enforced by pyright in strict mode

## Environment Variables (referenced by `bundle_roam_md.py` CLI args)
- `ROAM_LOCAL_API_PORT` — port for Roam Local API
- `ROAM_GRAPH_NAME` — Roam graph name
- `ROAM_API_TOKEN` — bearer token for auth
