"""Roam Research raw node data model.

Public symbols:

- :class:`RoamNode` — raw shape of a pull-block as returned by the Roam Local API.
- :data:`NodeNetwork` — a collection of :class:`RoamNode` instances.
- :class:`NodeTree` — a Pydantic-typed wrapper holding a :data:`NodeNetwork`.
- :meth:`NodeTree.dfs` — return a :class:`NodeTreeDFSIterator` for pre-order depth-first traversal.
- :class:`NodeTreeDFSIterator` — pre-order depth-first iterator over a :class:`NodeTree`.
- :func:`is_root` — return ``True`` when a node has no ancestors inside a :data:`NodeNetwork`.
- :func:`has_single_root` — :data:`~roam_pub.validation.Validator` requiring exactly one root node.
- :func:`all_children_present` — :data:`~roam_pub.validation.Validator` requiring all child ids in a
  :data:`NodeNetwork` to resolve to member nodes.
- :func:`all_parents_present` — :data:`~roam_pub.validation.Validator` requiring all parent ids in a
  :data:`NodeNetwork` to resolve to member nodes.
- :func:`has_unique_ids` — :data:`~roam_pub.validation.Validator` requiring every :attr:`~RoamNode.id`
  in a :data:`NodeNetwork` to be unique.
- :func:`is_acyclic` — :data:`~roam_pub.validation.Validator` requiring the child-edge graph of a
  :data:`NodeNetwork` to be cycle-free.
- :func:`is_tree` — validate all tree invariants against a :data:`NodeNetwork`; returns a
  :class:`~roam_pub.validation.ValidationResult`.
"""

import logging
from collections.abc import Iterator
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

from roam_pub.roam_primitives import (
    HeadingLevel,
    Id,
    IdObject,
    LinkObject,
    Order,
    PageTitle,
    RawChildren,
    RawRefs,
    Uid,
)
from roam_pub.roam_schema import RoamAttribute
from roam_pub.validation import ValidationError, ValidationResult, validate_all

logger = logging.getLogger(__name__)


class RoamNode(BaseModel):
    """Raw shape of a "pull-block" as returned by ``roamAlphaAPI.data.q`` / ``pull [*]``.

    This is the *un-normalized* form — property names mirror the raw Datomic
    attribute names, and nested refs are still IdObject stubs rather than resolved UIDs.

    All fields are optional except ``uid``, ``id``, ``time``, and ``user``,
    because the set of attributes present depends on the entity type (Page vs.
    Block) and which optional features (heading, text-align, etc.) were ever set.

    Attributes:
        uid: Nine-character stable block/page identifier (BLOCK_UID). Required.
        id: Datomic internal numeric entity id (:db/id). Ephemeral and not stable
            across exports. Required.
        time: Last-edit Unix timestamp in milliseconds (EDIT_TIME). Required.
        user: IdObject stub referencing the last-editing user entity. Required.
        string: Block text content (BLOCK_STRING). Present only on Block entities.
        title: Page title (NODE_TITLE). Present only on Page entities.
        order: Zero-based sibling order (BLOCK_ORDER). Present only on child Blocks.
        heading: HeadingLevel (BLOCK_HEADING). Present only on heading Blocks.
        children: Raw child block stubs (BLOCK_CHILDREN).
        refs: Raw page/block reference stubs (BLOCK_REFS).
        page: IdObject stub for the containing page (BLOCK_PAGE). Present only on Blocks.
        open: Whether the block is expanded (BLOCK_OPEN). Present only on Blocks.
        sidebar: Sidebar state. Present only on Pages.
        parents: IdObject stubs for all ancestor blocks (BLOCK_PARENTS). Present only on Blocks.
        props: Block property key-value map (BLOCK_PROPS). Present only on Blocks that have block
            properties set (e.g. ``ah-level`` from the Augmented Headings extension).
        attrs: Structured attribute assertions (ENTITY_ATTRS).
        lookup: IdObject stubs for ATTRS_LOOKUP. Purpose unclear.
        seen_by: IdObject stubs for EDIT_SEEN_BY. Purpose unclear.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    uid: Uid = Field(..., description=f"{RoamAttribute.BLOCK_UID} — nine-character stable identifier")
    id: Id = Field(..., description=":db/id — Datomic internal entity id (ephemeral)")
    time: int = Field(..., description=f"{RoamAttribute.EDIT_TIME} — last-edit Unix timestamp (ms)")
    user: IdObject = Field(..., description=f"{RoamAttribute.EDIT_USER} — last-editing user stub")

    # Block-only fields
    string: str | None = Field(
        default=None, description=f"{RoamAttribute.BLOCK_STRING} — block text; present only on Blocks"
    )
    order: Order | None = Field(
        default=None, description=f"{RoamAttribute.BLOCK_ORDER} — sibling order; present only on child Blocks"
    )
    heading: HeadingLevel | None = Field(
        default=None, description=f"{RoamAttribute.BLOCK_HEADING} — heading level; present only on heading Blocks"
    )
    children: RawChildren | None = Field(
        default=None, description=f"{RoamAttribute.BLOCK_CHILDREN} — raw child stubs; present only on Blocks"
    )
    refs: RawRefs | None = Field(
        default=None, description=f"{RoamAttribute.BLOCK_REFS} — raw reference stubs; present only on Blocks"
    )
    page: IdObject | None = Field(
        default=None, description=f"{RoamAttribute.BLOCK_PAGE} — containing page stub; present only on Blocks"
    )
    open: bool | None = Field(
        default=None, description=f"{RoamAttribute.BLOCK_OPEN} — expanded/collapsed state; present only on Blocks"
    )
    parents: list[IdObject] | None = Field(
        default=None, description=f"{RoamAttribute.BLOCK_PARENTS} — all ancestor stubs; present only on Blocks"
    )
    props: dict[str, object] | None = Field(
        default=None,
        description=(
            f"{RoamAttribute.BLOCK_PROPS} — block property key-value map; "
            "present only on Blocks that have block properties set (e.g. ``ah-level`` from Augmented Headings)."
        ),
    )

    # Page-only fields
    title: PageTitle | None = Field(
        default=None, description=f"{RoamAttribute.NODE_TITLE} — page title; present only on Pages"
    )
    sidebar: int | None = Field(
        default=None, description=f"{RoamAttribute.PAGE_SIDEBAR} — sidebar state; present only on Pages"
    )

    # Sparse / metadata fields
    attrs: list[list[LinkObject]] | None = Field(
        default=None, description=f"{RoamAttribute.ENTITY_ATTRS} — structured attribute assertions"
    )
    lookup: list[IdObject] | None = Field(
        default=None, description=f"{RoamAttribute.ATTRS_LOOKUP} — attribute lookup stubs (purpose unclear)"
    )
    seen_by: list[IdObject] | None = Field(
        default=None, description=f"{RoamAttribute.EDIT_SEEN_BY} — users who have seen this block (purpose unclear)"
    )


type NodeNetwork = list[RoamNode]
"""A collection of :class:`RoamNode` instances.

Relationships between nodes are encoded via :attr:`RoamNode.children`,
:attr:`RoamNode.parents`, and :attr:`RoamNode.page` as
:class:`~roam_pub.roam_primitives.IdObject` stubs referencing :attr:`RoamNode.id`
values within the collection.
"""


class NodeTree(BaseModel):
    """A Pydantic-typed wrapper holding a :data:`NodeNetwork`.

    Raises:
        pydantic.ValidationError: If *network* does not satisfy all tree invariants
            verified by :func:`is_tree`.

    Attributes:
        network: The constituent nodes of this tree.
        is_rooted: Whether this tree has a single root node. Defaults to ``True``.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    network: NodeNetwork = Field(..., description="The constituent nodes of this tree.")
    is_rooted: bool = Field(default=True, description="Whether this tree has a single root node.")

    @model_validator(mode="after")
    def _validate_is_tree(self) -> NodeTree:
        """Raise ValueError if *network* fails any tree invariant checked by is_tree."""
        result = is_tree(self.network, is_rooted=self.is_rooted)
        if not result.is_valid:
            messages = "; ".join(str(e) for e in result.errors)
            raise ValueError(messages)
        return self

    def dfs(self) -> NodeTreeDFSIterator:
        """Return a pre-order depth-first iterator over this tree.

        Returns:
            A :class:`NodeTreeDFSIterator` seeded at the root of this tree.
        """
        return NodeTreeDFSIterator(self)


class NodeTreeDFSIterator(Iterator[RoamNode]):
    """Pre-order depth-first iterator over a :class:`NodeTree`.

    Yields nodes starting from the single root, then recursively yields each
    child subtree in ascending :attr:`~RoamNode.order` order.  The traversal
    is non-recursive internally (stack-based), so deep trees do not risk
    hitting Python's recursion limit.

    Usage::

        for node in NodeTreeDFSIterator(tree):
            ...

    Attributes:
        _id_map: Mapping from :attr:`~RoamNode.id` to :class:`RoamNode`,
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
        root: RoamNode = next(n for n in tree.network if is_root(n, tree.network))
        self._stack: list[RoamNode] = [root]

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


def is_root(node: RoamNode, network: NodeNetwork) -> bool:
    """Return ``True`` when *node* has no ancestors inside *network*.

    A node is considered a root when its ``parents`` field is ``None`` or
    empty, or when none of its parent ids resolve to a node in *network*.

    Args:
        node: The candidate node to test.
        network: The collection of nodes used to resolve parent ids.

    Returns:
        ``True`` if *node* has no parents or no parents present in *network*;
        ``False`` otherwise.
    """
    if not node.parents:
        return True
    network_ids: set[Id] = {n.id for n in network}
    return not any(p.id in network_ids for p in node.parents)


def has_single_root(network: NodeNetwork) -> ValidationError | None:
    """Return ``None`` when *network* contains exactly one root node.

    A node is a root per :func:`is_root` — its :attr:`~RoamNode.parents` field is
    ``None`` or empty, or none of its parent ids resolve to a node in *network*.
    The validator fails if the root count is anything other than one.

    Args:
        network: The collection of nodes to validate.

    Returns:
        ``None`` if *network* has exactly one root; a
        :class:`~roam_pub.validation.ValidationError` describing the failure
        otherwise.
    """
    roots = [n for n in network if is_root(n, network)]
    if len(roots) == 1:
        return None
    root_uids = sorted(n.uid for n in roots)
    return ValidationError(
        message=f"expected exactly one root node; found {len(roots)}: {root_uids}", validator=has_single_root
    )


def all_children_present(network: NodeNetwork) -> ValidationError | None:
    """Return ``None`` when every child id referenced in *network* resolves to a node in *network*.

    Iterates every node in *network* and checks that each :attr:`~RoamNode.id`
    value found in a node's :attr:`~RoamNode.children` list corresponds to the
    :attr:`~RoamNode.id` of at least one node in *network*.

    A network with no children at all vacuously satisfies this condition and
    returns ``None``.

    Args:
        network: The collection of nodes to examine.

    Returns:
        ``None`` if every child id in *network* resolves to a node in *network*;
        a :class:`~roam_pub.validation.ValidationError` listing the sorted
        absent child ids and the sorted ids of the nodes that referenced them otherwise.
    """
    network_ids: Final[set[Id]] = {n.id for n in network}
    violations: Final[list[tuple[Id, Id]]] = [
        (n.id, child.id) for n in network if n.children for child in n.children if child.id not in network_ids
    ]
    if not violations:
        return None
    missing_ids: Final[list[Id]] = sorted({child_id for _, child_id in violations})
    node_ids: Final[list[Id]] = sorted({node_id for node_id, _ in violations})
    return ValidationError(
        message=f"child ids absent from network: {missing_ids}; referenced by nodes: {node_ids}",
        validator=all_children_present,
    )


def all_parents_present(network: NodeNetwork, *, is_rooted: bool = True) -> ValidationError | None:
    """Return ``None`` when every parent id referenced in *network* resolves to a node in *network*.

    Iterates every node in *network* and checks that each :attr:`~RoamNode.id`
    value found in a node's :attr:`~RoamNode.parents` list corresponds to the
    :attr:`~RoamNode.id` of at least one node in *network*.

    A network with no parents at all vacuously satisfies this condition and
    returns ``None``.

    When *is_rooted* is ``False``, root nodes (those for which :func:`is_root` returns
    ``True``) are excluded from the check, because their parents may legitimately
    reside outside the network.

    Args:
        network: The collection of nodes to examine.
        is_rooted: When ``True`` (default), every node's parents must be present in
            *network*.  When ``False``, root nodes are exempt from the check.

    Returns:
        ``None`` if every applicable parent id in *network* resolves to a node in
        *network*; a :class:`~roam_pub.validation.ValidationError` listing the sorted
        absent parent ids and the sorted ids of the nodes that referenced them otherwise.
    """
    network_ids: Final[set[Id]] = {n.id for n in network}
    nodes_to_check: Final[NodeNetwork] = network if is_rooted else [n for n in network if not is_root(n, network)]
    violations: Final[list[tuple[Id, Id]]] = [
        (n.id, parent.id) for n in nodes_to_check if n.parents for parent in n.parents if parent.id not in network_ids
    ]
    if not violations:
        return None
    missing_ids: Final[list[Id]] = sorted({parent_id for _, parent_id in violations})
    node_ids: Final[list[Id]] = sorted({node_id for node_id, _ in violations})
    return ValidationError(
        message=f"parent ids absent from network: {missing_ids}; referenced by nodes: {node_ids}",
        validator=all_parents_present,
    )


def has_unique_ids(network: NodeNetwork) -> ValidationError | None:
    """Return ``None`` when every :attr:`~RoamNode.id` in *network* is unique.

    Checks that no two nodes in *network* share the same :attr:`~RoamNode.id`
    value.  An empty network vacuously satisfies this condition.

    Args:
        network: The collection of nodes to examine.

    Returns:
        ``None`` if all node ids in *network* are distinct; a
        :class:`~roam_pub.validation.ValidationError` listing the sorted
        duplicate ids otherwise.
    """
    ids: list[Id] = [n.id for n in network]
    if len(ids) == len(set(ids)):
        return None
    seen: set[Id] = set()
    duplicates: set[Id] = set()
    for id_ in ids:
        if id_ in seen:
            duplicates.add(id_)
        seen.add(id_)
    dup_ids = sorted(duplicates)
    return ValidationError(message=f"expected unique node ids; found duplicates: {dup_ids}", validator=has_unique_ids)


def is_acyclic(network: NodeNetwork) -> ValidationError | None:
    """Return ``None`` when the child-edge graph of *network* contains no directed cycles.

    Performs a depth-first search over the :attr:`~RoamNode.children` edges of
    *network*, colouring each node white (unvisited), grey (on the current DFS
    path), or black (fully explored).  Encountering a grey node during
    traversal reveals a back-edge and therefore a cycle.

    Child references that point to nodes absent from *network* are silently
    skipped; use :func:`all_children_present` to validate referential
    integrity separately.

    An empty network vacuously satisfies this condition and returns ``None``.

    Args:
        network: The collection of nodes to examine.

    Returns:
        ``None`` if *network* contains no directed cycles; a
        :class:`~roam_pub.validation.ValidationError` naming the uid of the
        cycle-involved node otherwise.
    """
    id_to_node: dict[Id, RoamNode] = {n.id: n for n in network}
    _WHITE, _GREY, _BLACK = 0, 1, 2
    color: dict[Id, int] = {n.id: _WHITE for n in network}

    def _dfs(node_id: Id) -> Uid | None:
        """Return the uid of a cycle-involved node, or ``None`` if no cycle is found."""
        color[node_id] = _GREY
        node = id_to_node[node_id]
        if node.children:
            for child_stub in node.children:
                child_id = child_stub.id
                if child_id not in color:
                    continue  # child outside network — skip
                if color[child_id] == _GREY:
                    return id_to_node[child_id].uid  # back-edge → cycle detected
                if color[child_id] == _WHITE:
                    cycle_uid = _dfs(child_id)
                    if cycle_uid is not None:
                        return cycle_uid
        color[node_id] = _BLACK
        return None

    for n in network:
        if color[n.id] == _WHITE:
            cycle_uid = _dfs(n.id)
            if cycle_uid is not None:
                return ValidationError(
                    message=f"child-edge graph contains a directed cycle involving node '{cycle_uid}'",
                    validator=is_acyclic,
                )
    return None


def is_tree(network: NodeNetwork, *, is_rooted: bool = True) -> ValidationResult:
    """Return a :class:`~roam_pub.validation.ValidationResult` for all tree invariants on *network*.

    Runs every tree-invariant validator — :func:`has_unique_ids`, :func:`has_single_root`,
    :func:`all_children_present`, :func:`all_parents_present`, and :func:`is_acyclic` — via
    :func:`~roam_pub.validation.validate_all`.  All validators run regardless of prior failures;
    the result accumulates every error found.

    Args:
        network: The collection of nodes to validate.
        is_rooted: Forwarded to :func:`all_parents_present`.  When ``False``, root nodes are
            exempt from the parent-presence check.

    Returns:
        A :class:`~roam_pub.validation.ValidationResult` that is valid when *network* satisfies
        every tree invariant, or contains one :class:`~roam_pub.validation.ValidationError` per
        failed validator otherwise.
    """
    logger.debug("network=%r, is_rooted=%r", network, is_rooted)
    return validate_all(
        network,
        [
            has_unique_ids,
            has_single_root,
            all_children_present,
            lambda n: all_parents_present(n, is_rooted=is_rooted),
            is_acyclic,
        ],
    )
