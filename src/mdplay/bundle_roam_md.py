#!/usr/bin/env python3
"""
Script to bundle Roam Research Markdown files by fetching Firebase-hosted images
and replacing them with local file references.

Usage:
    python bundle_roam_md.py <markdown_file> <local_api_port> <graph_name> <output_dir>

Example:
    python bundle_roam_md.py my_notes.md 3333 SCFH ./output
"""

import sys
import logging
from pathlib import Path

from mdplay.roam_md_bundle import bundle_md_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the script."""
    if len(sys.argv) != 5:
        print("Usage: python bundle_roam_md.py <markdown_file> <local_api_port> <graph_name> <output_dir>")
        print()
        print("Example:")
        print("  python bundle_roam_md.py my_notes.md 3333 SCFH ./output")
        sys.exit(1)

    markdown_file: Path = Path(sys.argv[1])
    local_api_port: int = int(sys.argv[2])
    graph_name: str = sys.argv[3]
    output_dir: Path = Path(sys.argv[4])

    try:
        bundle_md_file(markdown_file, local_api_port, graph_name, output_dir)
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
