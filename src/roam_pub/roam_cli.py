"""Shared CLI utilities for Roam Research tree commands.

Public symbols:

- :func:`fetch_roam_trees` — resolve a target to a :class:`~roam_pub.roam_node.NodeTree`
  and :class:`~roam_pub.roam_graph.VertexTree`, ready for rendering or further processing.
"""

import logging
from typing import Final

import typer

from roam_pub.roam_graph import VertexTree
from roam_pub.roam_local_api import ApiEndpoint
from roam_pub.roam_node import NodeTree, RoamNode
from roam_pub.roam_node_fetch import FetchRoamNodes, TargetKind
from roam_pub.roam_primitives import UID_RE
from roam_pub.roam_transcribe import transcribe

logger = logging.getLogger(__name__)


def fetch_roam_trees(target: str, api_endpoint: ApiEndpoint) -> tuple[NodeTree, VertexTree]:
    """Fetch Roam nodes for *target* and build a validated node tree and vertex tree.

    Resolves *target* to a :data:`~roam_pub.roam_node_fetch.TargetKind`, fetches the
    corresponding :class:`~roam_pub.roam_node.RoamNode` records via *api_endpoint*,
    constructs a :class:`~roam_pub.roam_node.NodeTree` (with
    :attr:`~roam_pub.roam_node.NodeTree.is_standalone` set appropriately for the target
    kind), transcribes it to a :class:`~roam_pub.roam_graph.VertexTree`, and returns both.

    Exits the CLI with code 1 when the fetch raises an exception or when no nodes are found.

    Args:
        target: Roam page title or node UID.  Treated as a node UID if it matches
            :data:`~roam_pub.roam_primitives.UID_RE`; otherwise as a page title.
        api_endpoint: Configured API endpoint used to fetch nodes.

    Returns:
        A ``(node_tree, vertex_tree)`` pair ready for rendering or further processing.
    """
    target_kind: Final[TargetKind] = TargetKind.node if UID_RE.match(target) else TargetKind.page
    logger.debug("target_kind=%r", target_kind)
    try:
        nodes: Final[list[RoamNode]] = FetchRoamNodes.fetch_roam_nodes(
            target=target, target_kind=target_kind, api_endpoint=api_endpoint
        )
    except Exception as e:
        logger.error("Error fetching %r: %s", target, e)
        raise typer.Exit(code=1)

    if not nodes:
        logger.info("No Roam nodes found for %r — aborting.", target)
        raise typer.Exit(code=1)

    node_tree: Final[NodeTree] = NodeTree(network=nodes, is_standalone=target_kind is TargetKind.page)
    vertex_tree: Final[VertexTree] = transcribe(node_tree)
    logger.debug("node_tree=%r\n\nvertex_tree=%r", node_tree, vertex_tree)
    return node_tree, vertex_tree
