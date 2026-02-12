import logging
import pytest
from pathlib import Path
from typing import List, Tuple
from unittest.mock import Mock, patch, mock_open
from pydantic import HttpUrl

from mdplay.roam_md_bundle import (
    find_markdown_image_links,
    fetch_and_save_image,
    replace_image_links,
    normalize_link_text,
    bundle_md_file,
)
from mdplay.roam_asset import ApiEndpointURL, RoamAsset, FetchRoamAsset
from datetime import datetime

logger = logging.getLogger(__name__)


class TestFindMarkdownImageLinks:
    """Tests for the find_markdown_image_links function."""

    def test_finds_single_firebase_link(self) -> None:
        """Test finding a single Firebase image link."""
        markdown_text: str = "![alt text](https://firebasestorage.googleapis.com/v0/b/firescript-577a2.appspot.com/o/imgs%2Fapp%2FSCFH%2F-9owRBegJ8.jpeg.enc?alt=media&token=abc123)"

        matches: List[Tuple[str, HttpUrl]] = find_markdown_image_links(markdown_text)

        assert len(matches) == 1
        assert str(matches[0][1]) == "https://firebasestorage.googleapis.com/v0/b/firescript-577a2.appspot.com/o/imgs%2Fapp%2FSCFH%2F-9owRBegJ8.jpeg.enc?alt=media&token=abc123"
        assert isinstance(matches[0][1], HttpUrl)

    def test_finds_multiple_firebase_links(self) -> None:
        """Test finding multiple Firebase image links."""
        markdown_text: str = """
        ![image1](https://firebasestorage.googleapis.com/v0/b/test1.appspot.com/o/img1.png?token=abc)
        Some text here
        ![image2](https://firebasestorage.googleapis.com/v0/b/test2.appspot.com/o/img2.jpg?token=def)
        """

        matches: List[Tuple[str, HttpUrl]] = find_markdown_image_links(markdown_text)

        assert len(matches) == 2
        assert "img1.png" in str(matches[0][1])
        assert "img2.jpg" in str(matches[1][1])
        assert isinstance(matches[0][1], HttpUrl)
        assert isinstance(matches[1][1], HttpUrl)

    def test_ignores_non_firebase_links(self) -> None:
        """Test that non-Firebase URLs are ignored."""
        markdown_text: str = """
        ![local](./local-image.png)
        ![remote](https://example.com/image.jpg)
        ![firebase](https://firebasestorage.googleapis.com/v0/b/test.appspot.com/o/img.png?token=abc)
        """

        matches: List[Tuple[str, HttpUrl]] = find_markdown_image_links(markdown_text)

        assert len(matches) == 1
        assert "firebasestorage.googleapis.com" in str(matches[0][1])
        assert isinstance(matches[0][1], HttpUrl)

    def test_empty_markdown_returns_empty_list(self) -> None:
        """Test that empty markdown returns empty list."""
        markdown_text: str = ""

        matches: List[Tuple[str, HttpUrl]] = find_markdown_image_links(markdown_text)

        assert len(matches) == 0

    def test_markdown_without_images_returns_empty_list(self) -> None:
        """Test that markdown without images returns empty list."""
        markdown_text: str = "# Heading\n\nSome text without any images."

        matches: List[Tuple[str, HttpUrl]] = find_markdown_image_links(markdown_text)

        assert len(matches) == 0

    def test_handles_multiline_alt_text(self) -> None:
        """Test that multiline alt text is handled correctly."""
        markdown_text: str = """![This is
        multiline
        alt text](https://firebasestorage.googleapis.com/v0/b/test.appspot.com/o/img.png?token=abc)"""

        matches: List[Tuple[str, HttpUrl]] = find_markdown_image_links(markdown_text)

        assert len(matches) == 1
        assert "firebasestorage.googleapis.com" in str(matches[0][1])
        assert isinstance(matches[0][1], HttpUrl)

    def test_returns_full_match_and_url(self) -> None:
        """Test that function returns both full match and URL."""
        markdown_text: str = "![alt](https://firebasestorage.googleapis.com/v0/b/test.appspot.com/o/img.png?token=abc)"

        matches: List[Tuple[str, HttpUrl]] = find_markdown_image_links(markdown_text)

        full_match, url = matches[0]
        assert full_match.startswith("![")
        assert full_match.endswith(")")
        assert str(url).startswith("https://firebasestorage.googleapis.com")
        assert isinstance(url, HttpUrl)


class TestFetchAndSaveImage:
    """Tests for the fetch_and_save_image function."""

    @patch('mdplay.roam_md_bundle.FetchRoamAsset.fetch')
    @patch('builtins.open', new_callable=mock_open)
    def test_fetches_and_saves_image_successfully(self, mock_file: Mock, mock_fetch: Mock) -> None:
        """Test successful image fetch and save."""
        # Setup
        api_endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="test-graph")
        firebase_url: HttpUrl = HttpUrl("https://firebasestorage.googleapis.com/v0/b/test.appspot.com/o/img.png?token=abc")
        output_dir: Path = Path("/tmp/test")

        mock_roam_asset: RoamAsset = RoamAsset(
            file_name="test_image.png",
            last_modified=datetime.now(),
            media_type="image/png",
            contents=b"fake image data"
        )
        mock_fetch.return_value = mock_roam_asset

        # Execute
        result_url, result_filename = fetch_and_save_image(api_endpoint, firebase_url, output_dir)

        # Verify
        assert result_url == firebase_url
        assert isinstance(result_url, HttpUrl)
        assert result_filename == "test_image.png"
        mock_fetch.assert_called_once()
        mock_file.assert_called_once_with(output_dir / "test_image.png", "wb")

    @patch('mdplay.roam_md_bundle.FetchRoamAsset.fetch')
    def test_fetch_failure_raises_exception(self, mock_fetch: Mock) -> None:
        """Test that fetch failure raises an exception."""
        api_endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="test-graph")
        firebase_url: HttpUrl = HttpUrl("https://firebasestorage.googleapis.com/v0/b/test.appspot.com/o/img.png?token=abc")
        output_dir: Path = Path("/tmp/test")

        mock_fetch.side_effect = Exception("Network error")

        with pytest.raises(Exception, match="Network error"):
            fetch_and_save_image(api_endpoint, firebase_url, output_dir)


class TestReplaceImageLinks:
    """Tests for the replace_image_links function."""

    def test_replaces_single_url(self) -> None:
        """Test replacing a single URL."""
        markdown_text: str = "![alt](https://firebasestorage.googleapis.com/o/img.png)"
        url_replacements: List[Tuple[HttpUrl, str]] = [
            (HttpUrl("https://firebasestorage.googleapis.com/o/img.png"), "local_image.png")
        ]

        result: str = replace_image_links(markdown_text, url_replacements)

        assert "local_image.png" in result
        assert "firebasestorage.googleapis.com" not in result

    def test_replaces_multiple_urls(self) -> None:
        """Test replacing multiple URLs."""
        markdown_text: str = """
        ![img1](https://firebasestorage.googleapis.com/o/img1.png)
        ![img2](https://firebasestorage.googleapis.com/o/img2.jpg)
        """
        url_replacements: List[Tuple[HttpUrl, str]] = [
            (HttpUrl("https://firebasestorage.googleapis.com/o/img1.png"), "local1.png"),
            (HttpUrl("https://firebasestorage.googleapis.com/o/img2.jpg"), "local2.jpg")
        ]

        result: str = replace_image_links(markdown_text, url_replacements)

        assert "local1.png" in result
        assert "local2.jpg" in result
        assert "firebasestorage.googleapis.com" not in result

    def test_empty_replacements_returns_original(self) -> None:
        """Test that empty replacements list returns original text."""
        markdown_text: str = "![alt](https://firebasestorage.googleapis.com/o/img.png)"
        url_replacements: List[Tuple[HttpUrl, str]] = []

        result: str = replace_image_links(markdown_text, url_replacements)

        assert result == markdown_text

    def test_preserves_markdown_structure(self) -> None:
        """Test that markdown structure is preserved."""
        markdown_text: str = "# Heading\n\n![image](https://firebasestorage.googleapis.com/o/img.png)\n\nSome text"
        url_replacements: List[Tuple[HttpUrl, str]] = [
            (HttpUrl("https://firebasestorage.googleapis.com/o/img.png"), "local.png")
        ]

        result: str = replace_image_links(markdown_text, url_replacements)

        assert "# Heading" in result
        assert "Some text" in result
        assert "local.png" in result


class TestNormalizeLinkText:
    """Tests for the normalize_link_text function."""

    def test_normalizes_multiline_image_link_text(self) -> None:
        """Test that multi-line image link text is normalized to single line."""
        markdown_text: str = "![A\nflower](image.png)"
        result: str = normalize_link_text(markdown_text)
        assert result == "![A flower](image.png)"

    def test_normalizes_multiline_regular_link_text(self) -> None:
        """Test that multi-line regular link text is normalized to single line."""
        markdown_text: str = "[Click\nhere](https://example.com)"
        result: str = normalize_link_text(markdown_text)
        assert result == "[Click here](https://example.com)"

    def test_handles_multiple_newlines_in_link_text(self) -> None:
        """Test that multiple consecutive newlines are replaced with single space."""
        markdown_text: str = "![Alt\n\n\ntext](image.png)"
        result: str = normalize_link_text(markdown_text)
        assert result == "![Alt text](image.png)"

    def test_normalizes_multiple_links_in_text(self) -> None:
        """Test that multiple links in the same text are all normalized."""
        markdown_text: str = "![First\nimage](img1.png) and [Second\nlink](url.com)"
        result: str = normalize_link_text(markdown_text)
        assert result == "![First image](img1.png) and [Second link](url.com)"

    def test_preserves_single_line_links(self) -> None:
        """Test that links without line breaks are unchanged."""
        markdown_text: str = "![Single line](image.png) and [normal link](url.com)"
        result: str = normalize_link_text(markdown_text)
        assert result == "![Single line](image.png) and [normal link](url.com)"

    def test_preserves_non_link_content(self) -> None:
        """Test that text outside of links is not modified."""
        markdown_text: str = """# Heading
Some paragraph text
![Image\nwith breaks](img.png)
More text"""
        result: str = normalize_link_text(markdown_text)
        assert "# Heading" in result
        assert "Some paragraph text" in result
        assert "More text" in result
        assert "![Image with breaks](img.png)" in result


class TestBundleMdFile:
    """Tests for the bundle_md_file function."""

    def test_file_not_found_raises_exception(self, tmp_path: Path) -> None:
        """Test that non-existent file raises FileNotFoundError."""
        markdown_file: Path = tmp_path / "nonexistent_file.md"

        with pytest.raises(FileNotFoundError, match="Markdown file not found"):
            bundle_md_file(markdown_file, 3333, "test-graph", tmp_path)

    @patch('mdplay.roam_md_bundle.find_markdown_image_links')
    def test_no_firebase_links_exits_early(self, mock_find: Mock, tmp_path: Path) -> None:
        """Test that function exits early when no Firebase links found."""
        # Create separate input and output directories
        input_dir: Path = tmp_path / "input"
        output_dir: Path = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        # Create a temporary markdown file in input directory
        markdown_file: Path = input_dir / "test.md"
        markdown_file.write_text("# Test\n\nNo images here.")

        mock_find.return_value = []

        # Should not raise exception
        bundle_md_file(markdown_file, 3333, "test-graph", output_dir)

        # Verify no output file was created since no Firebase links were found
        output_file: Path = output_dir / "test.md"
        assert not output_file.exists()

    @patch('mdplay.roam_md_bundle.fetch_and_save_image')
    @patch('mdplay.roam_md_bundle.find_markdown_image_links')
    def test_processes_file_successfully(self, mock_find: Mock, mock_fetch: Mock, tmp_path: Path) -> None:
        """Test successful file processing."""
        # Create separate input and output directories
        input_dir: Path = tmp_path / "input"
        output_dir: Path = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        # Create a temporary markdown file in input directory
        markdown_file: Path = input_dir / "test.md"
        markdown_content: str = "![image](https://firebasestorage.googleapis.com/o/img.png)"
        markdown_file.write_text(markdown_content)

        # Mock finding links
        mock_find.return_value = [
            ("![image](https://firebasestorage.googleapis.com/o/img.png)",
             "https://firebasestorage.googleapis.com/o/img.png")
        ]

        # Mock fetching and saving
        mock_fetch.return_value = ("https://firebasestorage.googleapis.com/o/img.png", "local_image.png")

        # Execute
        bundle_md_file(markdown_file, 3333, "test-graph", output_dir)

        # Verify output file was created
        output_file: Path = output_dir / "test.md"
        assert output_file.exists()

        # Verify content was updated
        output_content: str = output_file.read_text()
        assert "local_image.png" in output_content
        assert "firebasestorage.googleapis.com" not in output_content

    @patch('mdplay.roam_md_bundle.fetch_and_save_image')
    @patch('mdplay.roam_md_bundle.find_markdown_image_links')
    def test_continues_on_fetch_error(self, mock_find: Mock, mock_fetch: Mock, tmp_path: Path) -> None:
        """Test that processing continues when one image fetch fails."""
        # Create separate input and output directories
        input_dir: Path = tmp_path / "input"
        output_dir: Path = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        # Create a temporary markdown file in input directory
        markdown_file: Path = input_dir / "test.md"
        markdown_content: str = """
        ![image1](https://firebasestorage.googleapis.com/o/img1.png)
        ![image2](https://firebasestorage.googleapis.com/o/img2.png)
        """
        markdown_file.write_text(markdown_content)

        # Mock finding links
        mock_find.return_value = [
            ("![image1](https://firebasestorage.googleapis.com/o/img1.png)",
             "https://firebasestorage.googleapis.com/o/img1.png"),
            ("![image2](https://firebasestorage.googleapis.com/o/img2.png)",
             "https://firebasestorage.googleapis.com/o/img2.png")
        ]

        # Mock first fetch to fail, second to succeed
        mock_fetch.side_effect = [
            Exception("Network error"),
            ("https://firebasestorage.googleapis.com/o/img2.png", "local_image2.png")
        ]

        # Execute - should not raise exception
        bundle_md_file(markdown_file, 3333, "test-graph", output_dir)

        # Verify output file was still created
        output_file: Path = output_dir / "test.md"
        assert output_file.exists()

        # Verify second image was replaced
        output_content: str = output_file.read_text()
        assert "local_image2.png" in output_content
