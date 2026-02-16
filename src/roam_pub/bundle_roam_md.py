#!/usr/bin/env python3
"""
Script to bundle Roam Research Markdown files by fetching Firebase-hosted images
and replacing them with local file references.

Example:
    bundle-roam-md -m my_notes.md -p 3333 -g SCFH -t your-bearer-token -o ./output
"""

import logging
from pathlib import Path

import typer
from typing_extensions import Annotated

from roam_pub.roam_md_bundle import bundle_md_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = typer.Typer()


@app.command()
def main(
    markdown_file: Annotated[Path, typer.Option("--markdown-file", "-m", help="Path to the Markdown file to process")],
    local_api_port: Annotated[int, typer.Option("--port", "-p", help="Port for Roam Local API")],
    graph_name: Annotated[str, typer.Option("--graph", "-g", help="Name of the Roam graph")],
    api_bearer_token: Annotated[
        str, typer.Option("--token", "-t", help="Bearer token for Roam Local API authentication")
    ],
    output_dir: Annotated[Path, typer.Option("--output", "-o", help="Directory where bundle should be saved")],
) -> None:
    """
    Bundle a Roam Research Markdown file by fetching Firebase-hosted images
    and replacing them with local file references.

    Creates a .bundle directory containing the updated markdown file and all images.
    """
    # Create bundle directory: <output_dir>/<markdown_file_name>.bundle/
    bundle_dir_name: str = f"{markdown_file.name}.bundle"
    bundle_dir: Path = output_dir / bundle_dir_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created bundle directory: {bundle_dir}")

    try:
        bundle_md_file(markdown_file, local_api_port, graph_name, api_bearer_token, bundle_dir)
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
