#!/bin/bash
# Wrapper script to run export_roam_tree.py with the correct Python environment
#
# Usage: ./export-roam-tree.sh <page_title_or_node_uid> [--port <port>] [--graph <graph>] [--token <token>]
#                              [--output-dir <dir>] [--bundle|--no-bundle] [--cache-dir <dir>]
#
# Environment variables (may be set instead of CLI flags):
#   ROAM_LOCAL_API_PORT  — port for Roam Local API
#   ROAM_GRAPH_NAME      — name of the Roam graph
#   ROAM_API_TOKEN       — bearer token for Roam Local API authentication
#   ROAM_EXPORT_DIR      — output directory for the exported document
#   ROAM_CACHE_DIR       — directory for caching downloaded Cloud Firestore assets

# Get the repo root (one level above this script's directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Activate the virtual environment
source "$REPO_ROOT/.venv/bin/activate"

# Run the entry point with all arguments
export-roam-tree "$@"
