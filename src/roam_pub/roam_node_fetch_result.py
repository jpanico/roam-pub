"""Roam Research node-fetch result types.

Public symbols:

- :class:`QueryAnchorKind` — enum discriminating a page-title anchor from a node-UID anchor.
- :class:`NodeFetchAnchor` — immutable model pairing a raw anchor string with its detected kind.
- :class:`NodeFetchSpec` — immutable model pairing a :class:`NodeFetchAnchor` with fetch options.
- :class:`NodeFetchResult` — immutable model bundling the fetch anchor, its resolved node tree,
  and a :data:`~roam_pub.roam_node.NodesByUid` index of all fetched nodes.
- :data:`NodeFetchResult_Placeholder` — flat list of :class:`~roam_pub.roam_node.RoamNode` records
  returned by all :class:`~roam_pub.roam_node_fetch.FetchRoamNodes` fetch methods.
- :func:`anchor_node` — return the :class:`~roam_pub.roam_node.RoamNode` in a
  :data:`~roam_pub.roam_network.NodeNetwork` that matches a :class:`NodeFetchAnchor`.
- :func:`anchor_tree` — return the subtree of a :data:`~roam_pub.roam_network.NodeNetwork`
  rooted at the node that matches a :class:`NodeFetchAnchor`.
"""

import enum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, computed_field

from roam_pub.roam_network import NodeNetwork
from roam_pub.roam_node import NodesByUid, RoamNode
from roam_pub.roam_primitives import UID_RE
from roam_pub.roam_tree import NodeTree


@enum.unique
class QueryAnchorKind(enum.Enum):
    """Discriminates the kind of anchor passed to :class:`~roam_pub.roam_node_fetch.FetchRoamNodes` fetch methods.

    Attributes:
        PAGE_TITLE: The anchor is a Roam page title string.
        NODE_UID: The anchor is a nine-character ``:block/uid`` string.
    """

    PAGE_TITLE = enum.auto()
    NODE_UID = enum.auto()

    @staticmethod
    def of(target: str) -> QueryAnchorKind:
        """Return the :class:`QueryAnchorKind` for *target*.

        Args:
            target: A Roam page title or nine-character node UID.

        Returns:
            :attr:`NODE_UID` when *target* matches
            :data:`~roam_pub.roam_primitives.UID_RE`; :attr:`PAGE_TITLE` otherwise.
        """
        return QueryAnchorKind.NODE_UID if UID_RE.match(target) else QueryAnchorKind.PAGE_TITLE


class NodeFetchAnchor(BaseModel):
    """Immutable model pairing a raw anchor string with its derived :class:`QueryAnchorKind`.

    Attributes:
        qualifier: The raw anchor string — either a Roam page title or a nine-character node UID.
        kind: Derived from *qualifier* via :meth:`QueryAnchorKind.of`.
    """

    model_config = ConfigDict(frozen=True)

    qualifier: str = Field(description="A Roam page title or nine-character node UID.")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def kind(self) -> QueryAnchorKind:
        """Derive the :class:`QueryAnchorKind` from :attr:`qualifier`."""
        return QueryAnchorKind.of(self.qualifier)


class NodeFetchSpec(BaseModel):
    """Immutable model pairing a fetch anchor with its fetch options.

    Attributes:
        anchor: The fetch anchor identifying the root node by page title or node UID.
        include_refs: When ``True``, the fetch includes every node referenced via
            ``:block/refs`` from the anchor node or any of its descendants.
            When ``False``, only the anchor node and its descendant blocks are fetched.
    """

    model_config = ConfigDict(frozen=True)

    anchor: NodeFetchAnchor = Field(description="The fetch anchor identifying the root node.")
    include_refs: bool = Field(description="Whether to include :block/refs targets in the fetch.")


class NodeFetchResult(BaseModel):
    """Immutable model bundling a fetch anchor with its resolved node tree and UID index.

    Attributes:
        fetch_anchor: The anchor used to perform the fetch.
        anchor_tree: The :class:`~roam_pub.roam_tree.NodeTree` rooted at the fetch anchor.
        nodes_by_uid: Index mapping each fetched node's UID to its
            :class:`~roam_pub.roam_node.RoamNode`.
    """

    model_config = ConfigDict(frozen=True)

    fetch_anchor: NodeFetchAnchor = Field(description="The anchor used to perform the fetch.")
    anchor_tree: NodeTree = Field(description="The node tree rooted at the fetch anchor.")
    nodes_by_uid: NodesByUid = Field(description="Index mapping each fetched node UID to its RoamNode.")


type NodeFetchResult_Placeholder = NodeNetwork
"""Flat list of :class:`~roam_pub.roam_node.RoamNode` records returned by all public fetch methods."""


def anchor_node(network: NodeNetwork, anchor: NodeFetchAnchor) -> RoamNode:
    """Return the node in *network* that matches *anchor*.

    Args:
        network: The node network to search.
        anchor: The fetch anchor whose :attr:`~NodeFetchAnchor.qualifier` string identifies
            the anchor node — matched against :attr:`~roam_pub.roam_node.RoamNode.uid`
            for :attr:`~QueryAnchorKind.NODE_UID` anchors, or against
            :attr:`~roam_pub.roam_node.RoamNode.title` for :attr:`~QueryAnchorKind.PAGE_TITLE`
            anchors.

    Returns:
        The matching :class:`~roam_pub.roam_node.RoamNode`.

    Raises:
        ValueError: If no node in *network* matches *anchor*.
    """
    if anchor.kind is QueryAnchorKind.NODE_UID:
        found: RoamNode | None = next((n for n in network if n.uid == anchor.qualifier), None)
    else:
        found = next((n for n in network if n.title == anchor.qualifier), None)
    if found is None:
        raise ValueError(f"no node found in network matching anchor {anchor.qualifier!r} (kind={anchor.kind!r})")
    return found


def anchor_tree(network: NodeNetwork, anchor: NodeFetchAnchor) -> NodeNetwork:
    """Return all nodes in *network* reachable from the anchor node via :attr:`~roam_pub.roam_node.RoamNode.children`.

    Performs a depth-first traversal starting at the node identified by *anchor*,
    following ``:block/children`` references at every level.  The anchor node itself
    is always included in the result.

    Args:
        network: The node network to search.
        anchor: The fetch anchor identifying the root of the subtree.

    Returns:
        A :data:`~roam_pub.roam_network.NodeNetwork` containing the anchor node and
        every node transitively reachable through ``:block/children``, in DFS pre-order.

    Raises:
        ValueError: If no node in *network* matches *anchor*, or if a
            ``:block/children`` reference resolves to an ``:db/id`` that is not
            present in *network*.
    """
    id_to_node: Final[dict[int, RoamNode]] = {n.id: n for n in network}
    root: Final[RoamNode] = anchor_node(network, anchor)

    result: Final[list[RoamNode]] = []
    stack: Final[list[RoamNode]] = [root]
    visited: Final[set[int]] = set()

    while stack:
        node: RoamNode = stack.pop()
        if node.id in visited:
            continue
        visited.add(node.id)
        result.append(node)
        if not node.children:
            continue
        for child_ref in node.children:
            if child_ref.id not in id_to_node:
                raise ValueError(f"child id {child_ref.id!r} not found in network (parent uid={node.uid!r})")
            stack.append(id_to_node[child_ref.id])

    return result
