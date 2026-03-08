"""Shared tree-loading pipeline for Roam Research CLI commands.

Public symbols:

- :func:`fetch_roam_trees` — resolve a target to a :class:`~roam_pub.roam_tree.NodeTree`
  and :class:`~roam_pub.graph.VertexTree`, ready for rendering or further processing.
"""

import logging
from typing import Final

import typer

from roam_pub.graph import VertexTree
from roam_pub.roam_local_api import ApiEndpoint
from roam_pub.roam_node_fetch import FetchRoamNodes
from roam_pub.roam_node_fetch_result import NodeFetchAnchor, NodeFetchResult
from roam_pub.roam_tree import NodeTree
from roam_pub.roam_transcribe import transcribe

logger = logging.getLogger(__name__)


def fetch_roam_trees(
    anchor: NodeFetchAnchor, api_endpoint: ApiEndpoint, include_refs: bool = False
) -> tuple[NodeTree, VertexTree]:
    """Fetch Roam nodes for *anchor* and build a validated node tree and vertex tree.

    Fetches :class:`~roam_pub.roam_node.RoamNode` records for *anchor* via
    *api_endpoint*, constructs a :class:`~roam_pub.roam_tree.NodeTree`, transcribes it to a
    :class:`~roam_pub.graph.VertexTree`, and returns both.

    Exits the CLI with code 1 when the fetch raises an exception or when no nodes are found.

    Args:
        anchor: The resolved fetch anchor, carrying both the raw string and its detected kind.
        api_endpoint: Configured API endpoint used to fetch nodes.
        include_refs: When ``True``, also fetches every node referenced via
            ``:block/refs`` from the anchor page or any of its descendants.  Forwarded to
            :func:`~roam_pub.roam_node_fetch.FetchRoamNodes.fetch_roam_nodes`; ignored
            when *anchor* is a node UID.

    Returns:
        An ``(anchor_tree, vertex_tree)`` pair ready for rendering or further processing.
    """
    try:
        result: Final[NodeFetchResult] = FetchRoamNodes.fetch_roam_nodes(
            anchor=anchor, api_endpoint=api_endpoint, include_refs=include_refs
        )
    except Exception as e:
        logger.error("Error fetching %r: %s", anchor.qualifier, e)
        raise typer.Exit(code=1)

    anchor_tree: Final[NodeTree] = result.anchor_tree
    vertex_tree: Final[VertexTree] = transcribe(anchor_tree)
    logger.debug("node_tree=%r\n\nvertex_tree=%r", anchor_tree, vertex_tree)
    return anchor_tree, vertex_tree
