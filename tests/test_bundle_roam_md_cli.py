"""Tests for the bundle_roam_md CLI validation."""

import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer

from roam_pub.bundle_roam_md import main

logger = logging.getLogger(__name__)


class TestBundleRoamMdValidation:
    """Tests for CLI input validation."""

    def test_missing_markdown_file_raises_exit(self, tmp_path: Path) -> None:
        """Test that a missing markdown file causes typer.Exit."""
        nonexistent_file = tmp_path / "nonexistent.md"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with pytest.raises(typer.Exit) as exc_info:
            main(nonexistent_file, 3333, "test-graph", "test-token", output_dir)

        assert exc_info.value.exit_code == 1

    def test_markdown_file_is_directory_raises_exit(self, tmp_path: Path) -> None:
        """Test that providing a directory instead of file causes typer.Exit."""
        directory = tmp_path / "not_a_file"
        directory.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with pytest.raises(typer.Exit) as exc_info:
            main(directory, 3333, "test-graph", "test-token", output_dir)

        assert exc_info.value.exit_code == 1

    @patch("roam_pub.bundle_roam_md.bundle_md_file")
    def test_valid_file_calls_bundle_md_file(self, mock_bundle: Mock, tmp_path: Path) -> None:
        """Test that a valid file successfully calls bundle_md_file."""
        markdown_file = tmp_path / "test.md"
        markdown_file.write_text("# Test")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        main(markdown_file, 3333, "test-graph", "test-token", output_dir)

        mock_bundle.assert_called_once_with(markdown_file, 3333, "test-graph", "test-token", output_dir)

    @patch("roam_pub.bundle_roam_md.bundle_md_file")
    def test_bundle_md_file_exception_raises_exit(self, mock_bundle: Mock, tmp_path: Path) -> None:
        """Test that exceptions from bundle_md_file cause typer.Exit."""
        markdown_file = tmp_path / "test.md"
        markdown_file.write_text("# Test")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Make bundle_md_file raise an exception
        mock_bundle.side_effect = Exception("Processing error")

        with pytest.raises(typer.Exit) as exc_info:
            main(markdown_file, 3333, "test-graph", "test-token", output_dir)

        assert exc_info.value.exit_code == 1

    def test_unreadable_file_raises_exit(self, tmp_path: Path) -> None:
        """Test that an unreadable file causes typer.Exit."""
        markdown_file = tmp_path / "test.md"
        markdown_file.write_text("# Test")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Make file unreadable
        markdown_file.chmod(0o000)

        try:
            with pytest.raises(typer.Exit) as exc_info:
                main(markdown_file, 3333, "test-graph", "test-token", output_dir)

            assert exc_info.value.exit_code == 1
        finally:
            # Restore permissions for cleanup
            markdown_file.chmod(0o644)

    def test_missing_output_dir_raises_exit(self, tmp_path: Path) -> None:
        """Test that a missing output directory causes typer.Exit."""
        markdown_file = tmp_path / "test.md"
        markdown_file.write_text("# Test")
        nonexistent_dir = tmp_path / "nonexistent"

        with pytest.raises(typer.Exit) as exc_info:
            main(markdown_file, 3333, "test-graph", "test-token", nonexistent_dir)

        assert exc_info.value.exit_code == 1

    def test_output_dir_is_file_raises_exit(self, tmp_path: Path) -> None:
        """Test that providing a file instead of directory for output causes typer.Exit."""
        markdown_file = tmp_path / "test.md"
        markdown_file.write_text("# Test")
        not_a_directory = tmp_path / "not_a_directory"
        not_a_directory.write_text("I am a file")

        with pytest.raises(typer.Exit) as exc_info:
            main(markdown_file, 3333, "test-graph", "test-token", not_a_directory)

        assert exc_info.value.exit_code == 1

    def test_unwritable_output_dir_raises_exit(self, tmp_path: Path) -> None:
        """Test that an unwritable output directory causes typer.Exit."""
        markdown_file = tmp_path / "test.md"
        markdown_file.write_text("# Test")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Make directory unwritable
        output_dir.chmod(0o444)

        try:
            with pytest.raises(typer.Exit) as exc_info:
                main(markdown_file, 3333, "test-graph", "test-token", output_dir)

            assert exc_info.value.exit_code == 1
        finally:
            # Restore permissions for cleanup
            output_dir.chmod(0o755)
