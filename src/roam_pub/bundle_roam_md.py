#!/usr/bin/env python3
"""
Script to bundle Roam Research Markdown files by fetching Firebase-hosted images
and replacing them with local file references.

Usage:
    python bundle_roam_md.py <markdown_file> <local_api_port> <graph_name> <api_bearer_token> <output_dir>

Example:
    python bundle_roam_md.py my_notes.md 3333 SCFH your-bearer-token ./output
"""

import sys
import logging
from pathlib import Path

from roam_pub.roam_md_bundle import bundle_md_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the script."""
    if len(sys.argv) != 6:
        print(
            "Usage: python bundle_roam_md.py <markdown_file> <local_api_port> <graph_name> <api_bearer_token> <output_dir>"
        )
        print()
        print("Example:")
        print("  python bundle_roam_md.py my_notes.md 3333 SCFH your-bearer-token ./output")
        sys.exit(1)

    markdown_file: Path = Path(sys.argv[1])
    local_api_port: int = int(sys.argv[2])
    graph_name: str = sys.argv[3]
    api_bearer_token: str = sys.argv[4]
    output_dir: Path = Path(sys.argv[5])

    # Create bundle directory: <output_dir>/<markdown_file_name>.bundle/
    bundle_dir_name: str = f"{markdown_file.name}.bundle"
    bundle_dir: Path = output_dir / bundle_dir_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created bundle directory: {bundle_dir}")

    try:
        bundle_md_file(markdown_file, local_api_port, graph_name, api_bearer_token, bundle_dir)
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
