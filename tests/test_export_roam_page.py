"""Unit tests for roam_pub.export_roam_page."""

import logging
import pathlib
from unittest.mock import patch

import yaml
from typer.testing import CliRunner

from roam_pub.export_roam_page import app
from roam_pub.roam_node import RoamNode

_FIXTURES_YAML_DIR = pathlib.Path(__file__).parent / "fixtures" / "yaml"
_FIXTURES_MD_DIR = pathlib.Path(__file__).parent / "fixtures" / "markdown"


def _article_0_nodes() -> list[RoamNode]:
    """Load and return the "Test Article 0" NodeNetwork from its YAML fixture."""
    raw: list[dict[str, object]] = yaml.safe_load((_FIXTURES_YAML_DIR / "test_article_0_nodes.yaml").read_text())
    return [RoamNode.model_validate(r) for r in raw]


class TestExportRoamPageNoBundle:
    """Tests for export_roam_page in --no-bundle mode."""

    def test_no_bundle_writes_expected_markdown(self, tmp_path: pathlib.Path) -> None:
        """Test that --no-bundle exports the correct CommonMark document.

        Loads nodes from the test_article_0_nodes.yaml fixture, mocks the Roam
        Local API fetch, invokes the CLI with --no-bundle, and asserts that the
        written .md file matches test_article_0_expected.md.
        """
        nodes: list[RoamNode] = _article_0_nodes()
        runner: CliRunner = CliRunner()

        with patch(
            "roam_pub.export_roam_page.FetchRoamNodes.fetch_by_page_title",
            return_value=nodes,
        ):
            # configure_logging() runs at import time and installs a StreamHandler
            # on the root logger.  CliRunner closes its captured stream after invoke,
            # leaving a dangling handler that raises ValueError on the next write.
            # Temporarily clear root handlers to prevent that conflict.
            saved_handlers = logging.root.handlers[:]
            logging.root.handlers.clear()
            try:
                result = runner.invoke(
                    app,
                    [
                        "Test Article 0",
                        "--port",
                        "3333",
                        "--graph",
                        "SCFH",
                        "--token",
                        "tok",
                        "--output-dir",
                        str(tmp_path),
                        "--no-bundle",
                    ],
                )
            finally:
                logging.root.handlers = saved_handlers

        assert result.exit_code == 0, result.output
        output_file: pathlib.Path = tmp_path / "Test Article 0.md"
        assert output_file.exists()
        expected: str = (_FIXTURES_MD_DIR / "test_article_0_expected.md").read_text()
        assert output_file.read_text() == expected
