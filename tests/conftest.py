"""Shared pytest configuration and test infrastructure for the roam_pub test suite."""

import pathlib

import pytest
import yaml

from roam_pub.roam_graph import VertexTree, vertex_adapter
from roam_pub.roam_local_api import ApiEndpoint, ApiEndpointURL
from roam_pub.roam_node import NodeTree, RoamNode
from roam_pub.roam_primitives import IdObject

FIXTURES_YAML_DIR: pathlib.Path = pathlib.Path(__file__).parent / "fixtures" / "yaml"
"""Absolute path to the ``tests/fixtures/yaml/`` directory."""

FIXTURES_JSON_DIR: pathlib.Path = pathlib.Path(__file__).parent / "fixtures" / "json"
"""Absolute path to the ``tests/fixtures/json/`` directory."""

FIXTURES_IMAGES_DIR: pathlib.Path = pathlib.Path(__file__).parent / "fixtures" / "images"
"""Absolute path to the ``tests/fixtures/images/`` directory."""

FIXTURES_MD_DIR: pathlib.Path = pathlib.Path(__file__).parent / "fixtures" / "markdown"
"""Absolute path to the ``tests/fixtures/markdown/`` directory."""

STUB_TIME: int = 0
"""Stub value for ``RoamNode.time`` in tests where the timestamp is irrelevant."""

STUB_USER: IdObject = IdObject(id=1)
"""Stub value for ``RoamNode.user`` in tests where the user is irrelevant."""


@pytest.fixture
def api_endpoint() -> ApiEndpoint:
    """Return a minimal :class:`~roam_pub.roam_local_api.ApiEndpoint` for unit tests."""
    return ApiEndpoint(
        url=ApiEndpointURL(local_api_port=3333, graph_name="test-graph"),
        bearer_token="test-token",
    )


def article0_node_tree() -> NodeTree:
    """Load and return the ``Test Article 0`` :class:`~roam_pub.roam_node.NodeTree` from its YAML fixture."""
    raw: list[dict[str, object]] = yaml.safe_load((FIXTURES_YAML_DIR / "test_article_0_nodes.yaml").read_text())
    return NodeTree(network=[RoamNode.model_validate(r) for r in raw])


def article0_vertex_tree() -> VertexTree:
    """Load and return the ``Test Article 0`` :class:`~roam_pub.roam_graph.VertexTree` from its YAML fixture."""
    raw: list[dict[str, object]] = yaml.safe_load((FIXTURES_YAML_DIR / "test_article_0_vertices.yaml").read_text())
    return VertexTree(vertices=[vertex_adapter.validate_python(r) for r in raw])
