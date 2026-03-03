# CLAUDE.md

## Project Overview
Python 3.14 toolkit for bundling Roam Research markdown exports with their
Cloud Firestore-hosted images into self-contained `.mdbundle` directories.

## Setup
```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

## Key Commands
```bash
bundle-roam-md -m <file> -p <port> -g <graph> -t <token> -o <output_dir>
dump-roam-page "Page Title" -p <port> -g <graph> -t <token> [--mode v|n|vn] [--node-props <props>]

# Run the full check pipeline (format + lint + type check + tests) in one shot:
hatch run check

# Individual steps (run in this order):
pydocstringformatter --write src/ # reflow docstring content (PEP 257)
ruff format --preview src/        # fix structural formatting around docstrings
ruff check --fix src/ tests/      # lint + fix docstring style (Google convention)
black .                           # format code
pyright                           # type check (strict)
pytest                            # run tests
```

## Project Structure
- `src/roam_pub/` — main package
  - **CLI entry points**
    - `bundle_roam_md.py` — bundles a Roam export + Firestore images into `.mdbundle`
    - `dump_roam_page.py` — dumps a Roam page as a Rich tree to the terminal (`--mode v|n|vn`)
  - **Core logic**
    - `roam_md_bundle.py` — core bundling logic
    - `roam_transcribe.py` — transcribes `NodeTree` → `VertexTree` (normalized graph)
    - `rich.py` — Rich panel/tree rendering for `NodeTree` and `VertexTree`
    - `validation.py` — generic accumulator-pipeline validation framework
  - **Model layer**
    - `roam_primitives.py` — foundational type aliases, stub models, `IMAGE_LINK_RE` (dependency root)
    - `roam_node.py` — `RoamNode`, `NodeTree`, `NodeTreeDFSIterator`
    - `roam_graph.py` — `Vertex` union, `VertexTree`, `VertexTreeDFSIterator`
    - `roam_schema.py` — Datomic schema model types (`RoamNamespace`, etc.)
    - `roam_asset.py` — Cloud Firestore asset model
  - **API / fetching**
    - `roam_local_api.py` — `ApiEndpoint` model for the Roam Local API
    - `roam_node_fetch.py` — fetches `RoamNode` records via Local API
    - `roam_schema_fetch.py` — fetches Datomic schema via Local API
    - `roam_asset_fetch.py` — fetches Firestore assets via Local API
  - **Infrastructure**
    - `logging_config.py` — colorized logging (`configure_logging()`); reads `LOG_LEVEL` env var
- `scripts/` — shell wrapper scripts (`dump-roam-page.sh`, `bundle-roam-md.sh`)
- `tests/fixtures/` — sample markdown, images, JSON, YAML for tests

## Conventions
- Src layout: package lives under `src/roam_pub/`
- Line length: 120 chars (Black + Ruff)
- Docstrings: PEP 257 format (pydocstringformatter), Google style convention (Ruff)
- Tests: pytest, files named `test_*.py`
- **Strong typing**: all Python code must use type annotations throughout; no `Any` types; enforced by pyright in strict mode

## Modern Python Requirements (Python 3.14)
All code written or modified by Claude MUST follow these conventions — no exceptions:

- **Built-in generics**: always `list[x]`, `tuple[x, y]`, `dict[k, v]`, `set[x]` — never `List`, `Tuple`, `Dict`, `Set` from `typing`
- **Union syntax**: always `X | Y` and `X | None` — never `Union[X, Y]` or `Optional[X]`
- **Type aliases**: always `type Foo = ...` (PEP 695) — never `Foo: TypeAlias = ...` or bare `Foo = ...`
- **No `from __future__ import annotations`**: not needed in Python 3.14 (PEP 649 deferred evaluation is the default)
- **No string-quoted forward references**: never `"ClassName"` in annotations; if a forward reference is needed, reorder definitions so the referenced name is declared first
- **No `cast()`**: never use `typing.cast()`; fix the type properly instead
- **No `Any`**: never use `typing.Any`; use a precise type or a type variable

## Reference Docs
- `docs/roam-md.md` — Roam flavored Markdown vs. CommonMark differences (relevant to normalization work)

## Environment Variables (referenced by `bundle_roam_md.py` CLI args)
- `ROAM_LOCAL_API_PORT` — port for Roam Local API
- `ROAM_GRAPH_NAME` — Roam graph name
- `ROAM_API_TOKEN` — bearer token for auth
- `ROAM_CACHE_DIR` — directory for caching downloaded Cloud Firestore assets
