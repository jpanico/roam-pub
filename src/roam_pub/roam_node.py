"""Roam Research raw node data model.

Public symbols:

- :class:`RoamNode` — raw shape of a pull-block as returned by the Roam Local API.
- :data:`NodeNetwork` — a collection of :class:`RoamNode` instances.
- :class:`NodeTree` — a Pydantic-typed wrapper holding a :data:`NodeNetwork`.
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

from pydantic import BaseModel, ConfigDict, Field, model_validator

from roam_pub.roam_types import (
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
:class:`~roam_pub.roam_types.IdObject` stubs referencing :attr:`RoamNode.id`
values within the collection.
"""


class NodeTree(BaseModel):
    """A Pydantic-typed wrapper holding a :data:`NodeNetwork`.

    Raises:
        pydantic.ValidationError: If *network* does not satisfy all tree invariants
            verified by :func:`is_tree`.

    Attributes:
        network: The constituent nodes of this tree.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    network: NodeNetwork = Field(..., description="The constituent nodes of this tree.")

    @model_validator(mode="after")
    def _validate_is_tree(self) -> NodeTree:
        """Raise ValueError if *network* fails any tree invariant checked by is_tree."""
        result = is_tree(self.network)
        if not result.is_valid:
            messages = "; ".join(e.message for e in result.errors)
            raise ValueError(messages)
        return self


def is_root(node: RoamNode, network: NodeNetwork) -> bool:
    """Return ``True`` when *node* has no parents.

    A node is considered a root when its ``parents`` field is ``None`` or
    empty.

    Args:
        node: The candidate node to test.
        network: Unused; retained for call-site compatibility.

    Returns:
        ``True`` if *node* has no parents; ``False`` otherwise.
    """
    return not node.parents


def has_single_root(network: NodeNetwork) -> ValidationError | None:
    """Return ``None`` when *network* contains exactly one root node.

    A node is a root when its :attr:`~RoamNode.parents` field is ``None`` or
    empty.  The validator fails if the root count is anything other than one.

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
    return ValidationError(message=f"expected exactly one root node; found {len(roots)}: {root_uids}")


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
        absent child ids otherwise.
    """
    network_ids: set[Id] = {n.id for n in network}
    missing: set[Id] = {child.id for n in network if n.children for child in n.children if child.id not in network_ids}
    if not missing:
        return None
    missing_ids = sorted(missing)
    return ValidationError(message=f"child ids absent from network: {missing_ids}")


def all_parents_present(network: NodeNetwork) -> ValidationError | None:
    """Return ``None`` when every parent id referenced in *network* resolves to a node in *network*.

    Iterates every node in *network* and checks that each :attr:`~RoamNode.id`
    value found in a node's :attr:`~RoamNode.parents` list corresponds to the
    :attr:`~RoamNode.id` of at least one node in *network*.

    A network with no parents at all vacuously satisfies this condition and
    returns ``None``.

    Args:
        network: The collection of nodes to examine.

    Returns:
        ``None`` if every parent id in *network* resolves to a node in *network*;
        a :class:`~roam_pub.validation.ValidationError` listing the sorted
        absent parent ids otherwise.
    """
    network_ids: set[Id] = {n.id for n in network}
    missing: set[Id] = {parent.id for n in network if n.parents for parent in n.parents if parent.id not in network_ids}
    if not missing:
        return None
    missing_ids = sorted(missing)
    return ValidationError(message=f"parent ids absent from network: {missing_ids}")


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
    return ValidationError(message=f"expected unique node ids; found duplicates: {dup_ids}")


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
                    message=f"child-edge graph contains a directed cycle involving node '{cycle_uid}'"
                )
    return None


def is_tree(network: NodeNetwork) -> ValidationResult:
    """Return a :class:`~roam_pub.validation.ValidationResult` for all tree invariants on *network*.

    Runs every tree-invariant validator — :func:`has_unique_ids`, :func:`has_single_root`,
    :func:`all_children_present`, :func:`all_parents_present`, and :func:`is_acyclic` — via
    :func:`~roam_pub.validation.validate_all`.  All validators run regardless of prior failures;
    the result accumulates every error found.

    Args:
        network: The collection of nodes to validate.

    Returns:
        A :class:`~roam_pub.validation.ValidationResult` that is valid when *network* satisfies
        every tree invariant, or contains one :class:`~roam_pub.validation.ValidationError` per
        failed validator otherwise.
    """
    return validate_all(
        network,
        [has_unique_ids, has_single_root, all_children_present, all_parents_present, is_acyclic],
    )
