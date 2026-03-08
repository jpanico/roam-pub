"""Roam Research node-tree wrappers and traversal.

Public symbols:

- :class:`NodeTree` — a Pydantic-typed wrapper holding a :data:`~roam_pub.roam_node.NodeNetwork`.
- :meth:`NodeTree.dfs` — return a :class:`NodeTreeDFSIterator` for pre-order depth-first traversal.
- :class:`NodeTreeDFSIterator` — pre-order depth-first iterator over a :class:`NodeTree`.
- :func:`is_tree` — validate all tree invariants against a :data:`~roam_pub.roam_node.NodeNetwork`;
  returns a :class:`~roam_pub.validation.ValidationResult`.
"""

import logging
from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict, Field

from roam_pub.roam_network import (
    NodeNetwork,
    all_children_present,
    has_unique_ids,
    is_acyclic,
)
from roam_pub.roam_node import RoamNode
from roam_pub.roam_primitives import Id
from roam_pub.validation import ValidationResult, validate_all

logger = logging.getLogger(__name__)


class NodeTree(BaseModel):
    """A Pydantic-typed wrapper holding a :data:`~roam_pub.roam_node.NodeNetwork`.

    Attributes:
        root_node: The single root node of this tree.
        network: All constituent nodes of this tree, including *root_node*.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    root_node: RoamNode = Field(..., description="The single root node of this tree.")
    network: NodeNetwork = Field(..., description="All constituent nodes of this tree, including root_node.")

    def dfs(self) -> NodeTreeDFSIterator:
        """Return a pre-order depth-first iterator over this tree.

        Returns:
            A :class:`NodeTreeDFSIterator` seeded at the root of this tree.
        """
        return NodeTreeDFSIterator(self)


class NodeTreeDFSIterator(Iterator[RoamNode]):
    """Pre-order depth-first iterator over a :class:`NodeTree`.

    Yields nodes starting from the single root, then recursively yields each
    child subtree in ascending :attr:`~roam_pub.roam_node.RoamNode.order` order.  The traversal
    is non-recursive internally (stack-based), so deep trees do not risk
    hitting Python's recursion limit.

    Usage::

        for node in NodeTreeDFSIterator(tree):
            ...

    Attributes:
        _id_map: Mapping from :attr:`~roam_pub.roam_node.RoamNode.id` to :class:`~roam_pub.roam_node.RoamNode`,
            built once at construction time.
        _stack: LIFO stack of nodes yet to be visited; initialized with the
            root node.
    """

    def __init__(self, tree: NodeTree) -> None:
        """Initialize the iterator from *tree*.

        Builds an id-map over *tree.network* and seeds the stack with the
        single root node.

        Args:
            tree: The :class:`NodeTree` to traverse.
        """
        self._id_map: dict[Id, RoamNode] = {n.id: n for n in tree.network}
        self._stack: list[RoamNode] = [tree.root_node]

    def __iter__(self) -> Iterator[RoamNode]:
        """Return *self* (this object is its own iterator)."""
        return self

    def __next__(self) -> RoamNode:
        """Return the next node in pre-order depth-first traversal.

        Raises:
            StopIteration: When all nodes have been yielded.
        """
        if not self._stack:
            raise StopIteration
        node: RoamNode = self._stack.pop()
        if node.children:
            children: list[RoamNode] = sorted(
                [self._id_map[c.id] for c in node.children if c.id in self._id_map],
                key=lambda n: n.order if n.order is not None else 0,
            )
            self._stack.extend(reversed(children))
        return node


def is_tree(network: NodeNetwork) -> ValidationResult:
    """Return a :class:`~roam_pub.validation.ValidationResult` for all tree invariants on *network*.

    Runs every tree-invariant validator — :func:`~roam_pub.roam_node.has_unique_ids`,
    :func:`~roam_pub.roam_node.all_children_present`, and
    :func:`~roam_pub.roam_node.is_acyclic` — via
    :func:`~roam_pub.validation.validate_all`.  All validators run regardless of prior failures;
    the result accumulates every error found.

    Args:
        network: The collection of nodes to validate.

    Returns:
        A :class:`~roam_pub.validation.ValidationResult` that is valid when *network* satisfies
        every tree invariant, or contains one :class:`~roam_pub.validation.ValidationError` per
        failed validator otherwise.
    """
    logger.debug("network=%r", network)

    return validate_all(
        network,
        [
            has_unique_ids,
            all_children_present,
            is_acyclic,
        ],
    )
