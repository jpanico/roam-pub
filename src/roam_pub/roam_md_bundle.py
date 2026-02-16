"""
Functions for processing Roam Research Markdown files.

This module provides utilities for finding Firebase image links in Markdown files,
fetching images via the Roam Local API, and updating Markdown files with local references.
"""

import re
import logging
from pathlib import Path
from typing import List, Tuple
from pydantic import HttpUrl

from roam_pub.roam_asset import ApiEndpointURL, FetchRoamAsset, RoamAsset

logger = logging.getLogger(__name__)


def find_markdown_image_links(markdown_text: str) -> List[Tuple[str, HttpUrl]]:
    """
    Find all Markdown image links in the text.

    Args:
        markdown_text: The Markdown content to search

    Returns:
        List of tuples: (full_match, image_url)
        Example: [('![](https://firebase...)', HttpUrl('https://firebase...'))]
    """
    # Regex pattern for Markdown images: ![alt text](url)
    # Matches: ![...](...) where the URL is a Firebase storage URL
    # re.DOTALL makes . match newlines, allowing multi-line alt text
    pattern = r"!\[((?:[^\]]|\n)*?)\]\((https://firebasestorage\.googleapis\.com/[^\)]+)\)"

    matches: List[Tuple[str, HttpUrl]] = []
    for match in re.finditer(pattern, markdown_text):
        full_match: str = match.group(0)  # Full ![...](...)
        image_url_str: str = match.group(2)  # Just the URL as string
        image_url: HttpUrl = HttpUrl(image_url_str)  # Convert to HttpUrl
        matches.append((full_match, image_url))

    logger.info(f"Found {len(matches)} Firebase image links")
    return matches


def fetch_and_save_image(api_endpoint: ApiEndpointURL, firebase_url: HttpUrl, output_dir: Path) -> Tuple[HttpUrl, str]:
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

    # Fetch the file from Roam
    roam_asset: RoamAsset = FetchRoamAsset.fetch(api_endpoint=api_endpoint, firebase_url=firebase_url)

    # Save the file to the output directory
    output_path: Path = output_dir / roam_asset.file_name
    with open(output_path, "wb") as f:
        f.write(roam_asset.contents)

    logger.info(f"Saved image to: {output_path}")

    return (firebase_url, roam_asset.file_name)


def replace_image_links(markdown_text: str, url_replacements: List[Tuple[HttpUrl, str]]) -> str:
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
        # Replace the Firebase URL with the local filename (convert HttpUrl to string for replacement)
        updated_text = updated_text.replace(str(firebase_url), local_filename)
        logger.info(f"Replaced {firebase_url} with {local_filename}")

    return updated_text


def normalize_link_text(markdown_text: str) -> str:
    """
    Remove line breaks from link text in Markdown links.

    Markdown links should not have multi-line link text. This function finds all
    Markdown links (both images and regular links) and removes any line breaks
    within the link text portion, replacing them with spaces.

    Args:
        markdown_text: The Markdown content to normalize

    Returns:
        Markdown text with single-line link text
    """
    # Pattern to match both image links ![text](url) and regular links [text](url)
    # Captures: optional '!', link text (which may contain newlines), and url
    pattern = r"(!?\[)((?:[^\]]|\n)+?)(\]\([^\)]+\))"

    def replace_newlines(match: re.Match) -> str:
        prefix: str = match.group(1)  # '![' or '['
        link_text: str = match.group(2)  # The link text (may have newlines)
        suffix: str = match.group(3)  # '](url)'

        # Replace newlines in link text with spaces
        normalized_text: str = re.sub(r"\n+", " ", link_text)

        return f"{prefix}{normalized_text}{suffix}"

    return re.sub(pattern, replace_newlines, markdown_text)


def remove_escaped_double_brackets(markdown_text: str) -> str:
    """
    Remove escaped double brackets from Markdown text.

    Roam Research uses [[page links]] syntax which gets escaped to \\[\\[ and \\]\\]
    when exported. This function removes those escaped brackets.

    Args:
        markdown_text: The Markdown content to process

    Returns:
        Markdown text with escaped double brackets removed
    """
    # Remove escaped opening double brackets: \[\[
    text = markdown_text.replace(r"\[\[", "")
    # Remove escaped closing double brackets: \]\]
    text = text.replace(r"\]\]", "")
    return text


def fetch_all_images(
    image_links: List[Tuple[str, HttpUrl]], api_endpoint: ApiEndpointURL, output_dir: Path
) -> List[Tuple[HttpUrl, str]]:
    """
    Fetch and save all images from the provided list of image links.

    Args:
        image_links: List of (full_match, firebase_url) tuples
        api_endpoint: The Roam Local API endpoint
        output_dir: Directory where images should be saved

    Returns:
        List of (firebase_url, local_filename) tuples for successfully fetched images
    """
    url_replacements: List[Tuple[HttpUrl, str]] = []
    for full_match, firebase_url in image_links:
        try:
            firebase_url_result, local_filename = fetch_and_save_image(api_endpoint, firebase_url, output_dir)
            url_replacements.append((firebase_url_result, local_filename))
        except Exception as e:
            logger.error(f"Failed to fetch {firebase_url}: {e}")
            # Continue with other images

    return url_replacements


def bundle_md_file(markdown_file: Path, local_api_port: int, graph_name: str, output_dir: Path) -> None:
    """
    Bundle a Markdown file: fetch images and update links.

    Args:
        markdown_file: Path to the Markdown file
        local_api_port: Port for Roam Local API
        graph_name: Name of the Roam graph
        output_dir: Directory where bundle (translated md file and local images) should be saved

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
    image_links: List[Tuple[str, HttpUrl]] = find_markdown_image_links(markdown_text)

    if not image_links:
        logger.info("No Firebase image links found in the file")
        return

    # Create API endpoint
    api_endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=local_api_port, graph_name=graph_name)

    # Fetch and save all images
    url_replacements: List[Tuple[HttpUrl, str]] = fetch_all_images(image_links, api_endpoint, output_dir)

    # Replace URLs in the Markdown text
    if url_replacements:
        updated_text: str = replace_image_links(markdown_text, url_replacements)

        # Normalize link text to remove line breaks
        updated_text = normalize_link_text(updated_text)

        # Remove escaped double brackets from Roam page links
        updated_text = remove_escaped_double_brackets(updated_text)

        # Write the updated Markdown file
        output_file: Path = output_dir / markdown_file.name
        output_file.write_text(updated_text, encoding="utf-8")
        logger.info(f"Wrote updated Markdown to: {output_file}")
        logger.info(f"Successfully processed {len(url_replacements)} images")
    else:
        logger.warning("No images were successfully fetched")
