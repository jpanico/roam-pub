#!/usr/bin/env python3
"""Script to bundle Roam Research Markdown files with local image references.

Fetches Firebase-hosted images and replaces them with local file references.

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


def validate_markdown_file(markdown_file: Path) -> None:
    """Validate that the markdown file exists and is readable.

    Args:
        markdown_file: Path to the markdown file to validate

    Raises:
        typer.Exit: If validation fails (file doesn't exist, isn't a file, or isn't readable)
    """
    # Validate markdown file exists
    if not markdown_file.exists():
        logger.error(f"Markdown file not found: {markdown_file}")
        raise typer.Exit(code=1)

    # Validate markdown file is readable
    if not markdown_file.is_file():
        logger.error(f"Path is not a file: {markdown_file}")
        raise typer.Exit(code=1)

    try:
        # Test if file is readable by attempting to open it
        with markdown_file.open("r") as _:
            pass
    except PermissionError:
        logger.error(f"Permission denied reading file: {markdown_file}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Cannot read file {markdown_file}: {e}")
        raise typer.Exit(code=1)


def validate_output_dir(output_dir: Path) -> None:
    """Validate that the output directory exists, is a directory, and is writable.

    Args:
        output_dir: Path to the output directory to validate

    Raises:
        typer.Exit: If validation fails (doesn't exist, isn't a directory, or isn't writable)
    """
    # Validate output directory exists
    if not output_dir.exists():
        logger.error(f"Output directory not found: {output_dir}")
        raise typer.Exit(code=1)

    # Validate output directory is a directory
    if not output_dir.is_dir():
        logger.error(f"Output path is not a directory: {output_dir}")
        raise typer.Exit(code=1)

    # Validate output directory is writable
    if not output_dir.stat().st_mode & 0o200:  # Check write permission bit
        logger.error(f"Output directory is not writable: {output_dir}")
        raise typer.Exit(code=1)

    # Try to create a temporary file to verify write access
    try:
        test_file = output_dir / ".write_test_tmp"
        test_file.touch()
        test_file.unlink()
    except PermissionError:
        logger.error(f"Permission denied writing to directory: {output_dir}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Cannot write to directory {output_dir}: {e}")
        raise typer.Exit(code=1)


@app.command()
def main(
    markdown_file: Annotated[Path, typer.Option("--markdown-file", "-m", help="Path to the Markdown file to process")],
    local_api_port: Annotated[
        int,
        typer.Option(
            "--port",
            "-p",
            envvar="ROAM_LOCAL_API_PORT",
            help="Port for Roam Local API",
        ),
    ],
    graph_name: Annotated[
        str,
        typer.Option(
            "--graph",
            "-g",
            envvar="ROAM_GRAPH_NAME",
            help="Name of the Roam graph",
        ),
    ],
    api_bearer_token: Annotated[
        str,
        typer.Option(
            "--token",
            "-t",
            envvar="ROAM_API_TOKEN",
            help="Bearer token for Roam Local API authentication",
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Parent directory where .mdbundle folder will be created",
        ),
    ],
    cache_dir: Annotated[
        Path | None,
        typer.Option(
            "--cache-dir",
            "-c",
            help="Directory for caching downloaded Firebase assets across runs. Skips re-downloading unchanged assets.",
        ),
    ] = None,
) -> None:
    """Bundle a Roam Research Markdown file with local image references.

    Fetches Firebase-hosted images, replacing them with local file references.
    Creates a <markdown_file>.mdbundle/ directory in output_dir containing
    the updated markdown file and all downloaded images.
    """
    validate_markdown_file(markdown_file)
    validate_output_dir(output_dir)

    if cache_dir is not None:
        validate_output_dir(cache_dir)

    try:
        bundle_md_file(markdown_file, local_api_port, graph_name, api_bearer_token, output_dir, cache_dir)
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
