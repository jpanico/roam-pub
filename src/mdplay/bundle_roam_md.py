#!/usr/bin/env python3
"""
Script to bundle Roam Research Markdown files by fetching Firebase-hosted images
and replacing them with local file references.

Usage:
    python bundle_roam_md.py <markdown_file> <local_api_port> <graph_name>

Example:
    python bundle_roam_md.py my_notes.md 3333 SCFH
"""

import re
import sys
import logging
from pathlib import Path
from typing import List, Tuple
from pydantic import HttpUrl

from mdplay.fetch_roam_file import ApiEndpointURL, FetchRoamFile, RoamFile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def find_markdown_image_links(markdown_text: str) -> List[Tuple[str, str]]:
    """
    Find all Markdown image links in the text.

    Args:
        markdown_text: The Markdown content to search

    Returns:
        List of tuples: (full_match, image_url)
        Example: [('![](https://firebase...)', 'https://firebase...')]
    """
    # Regex pattern for Markdown images: ![alt text](url)
    # Matches: ![...](...) where the URL is a Firebase storage URL
    # re.DOTALL makes . match newlines, allowing multi-line alt text
    pattern = r"!\[((?:[^\]]|\n)*?)\]\((https://firebasestorage\.googleapis\.com/[^\)]+)\)"

    matches: List[Tuple[str, str]] = []
    for match in re.finditer(pattern, markdown_text):
        full_match: str = match.group(0)  # Full ![...](...)
        image_url: str = match.group(2)  # Just the URL
        matches.append((full_match, image_url))

    logger.info(f"Found {len(matches)} Firebase image links")
    return matches


def fetch_and_save_image(api_endpoint: ApiEndpointURL, firebase_url: str, output_dir: Path) -> Tuple[str, str]:
    """
    Fetch an image from Roam and save it locally.

    Args:
        api_endpoint: The Roam Local API endpoint
        firebase_url: The Firebase storage URL
        output_dir: Directory where the image should be saved

    Returns:
        Tuple of (firebase_url, local_file_path)

    Raises:
        Exception: If fetch or save fails
    """
    logger.info(f"Fetching image from: {firebase_url}")

    # Convert string URL to HttpUrl
    http_url: HttpUrl = HttpUrl(firebase_url)

    # Fetch the file from Roam
    roam_file: RoamFile = FetchRoamFile.fetch(api_endpoint=api_endpoint, firebase_url=http_url)

    # Save the file to the output directory
    output_path: Path = output_dir / roam_file.file_name
    with open(output_path, "wb") as f:
        f.write(roam_file.contents)

    logger.info(f"Saved image to: {output_path}")

    return (firebase_url, roam_file.file_name)


def replace_image_links(markdown_text: str, url_replacements: List[Tuple[str, str]]) -> str:
    """
    Replace Firebase URLs with local file paths in Markdown text.

    Args:
        markdown_text: The original Markdown content
        url_replacements: List of (firebase_url, local_filename) tuples

    Returns:
        Updated Markdown text with local file references
    """
    updated_text: str = markdown_text

    for firebase_url, local_filename in url_replacements:
        # Replace the Firebase URL with the local filename
        updated_text = updated_text.replace(firebase_url, local_filename)
        logger.info(f"Replaced {firebase_url} with {local_filename}")

    return updated_text


def process_markdown_file(markdown_file: Path, local_api_port: int, graph_name: str) -> None:
    """
    Process a Markdown file: fetch images and update links.

    Args:
        markdown_file: Path to the Markdown file
        local_api_port: Port for Roam Local API
        graph_name: Name of the Roam graph

    Raises:
        FileNotFoundError: If markdown file doesn't exist
        Exception: If processing fails
    """
    if not markdown_file.exists():
        raise FileNotFoundError(f"Markdown file not found: {markdown_file}")

    logger.info(f"Processing Markdown file: {markdown_file}")

    # Read the Markdown file
    markdown_text: str = markdown_file.read_text(encoding="utf-8")

    # Find all image links
    image_links: List[Tuple[str, str]] = find_markdown_image_links(markdown_text)

    if not image_links:
        logger.info("No Firebase image links found in the file")
        return

    # Create API endpoint
    api_endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=local_api_port, graph_name=graph_name)

    # Output directory (same as the Markdown file)
    output_dir: Path = markdown_file.parent

    # Fetch and save each image
    url_replacements: List[Tuple[str, str]] = []
    for full_match, firebase_url in image_links:
        try:
            firebase_url_str, local_filename = fetch_and_save_image(api_endpoint, firebase_url, output_dir)
            url_replacements.append((firebase_url_str, local_filename))
        except Exception as e:
            logger.error(f"Failed to fetch {firebase_url}: {e}")
            # Continue with other images

    # Replace URLs in the Markdown text
    if url_replacements:
        updated_text: str = replace_image_links(markdown_text, url_replacements)

        # Write the updated Markdown file
        output_file: Path = markdown_file.parent / f"{markdown_file.stem}_converted.md"
        output_file.write_text(updated_text, encoding="utf-8")
        logger.info(f"Wrote updated Markdown to: {output_file}")
        logger.info(f"Successfully processed {len(url_replacements)} images")
    else:
        logger.warning("No images were successfully fetched")


def main() -> None:
    """Main entry point for the script."""
    if len(sys.argv) != 4:
        print("Usage: python convert_roam_images.py <markdown_file> <local_api_port> <graph_name>")
        print()
        print("Example:")
        print("  python convert_roam_images.py my_notes.md 3333 SCFH")
        sys.exit(1)

    markdown_file: Path = Path(sys.argv[1])
    local_api_port: int = int(sys.argv[2])
    graph_name: str = sys.argv[3]

    try:
        process_markdown_file(markdown_file, local_api_port, graph_name)
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
