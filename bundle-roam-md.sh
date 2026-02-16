#!/bin/bash
# Wrapper script to run bundle_roam_md.py with the correct Python environment
#
# Usage: ./bundle-roam-md.sh <markdown_file> <local_api_port> <graph_name> <api_bearer_token> <output_dir>

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate the virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Run the Python script with all arguments
python "$SCRIPT_DIR/src/roam_pub/bundle_roam_md.py" "$@"
