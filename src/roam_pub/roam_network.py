"""Roam Research node-network type and validators.

Public symbols:

- :data:`NodeNetwork` — a collection of :class:`~roam_pub.roam_node.RoamNode` instances.
- :func:`all_children_present` — :data:`~roam_pub.validation.Validator` requiring all child ids in a
  :data:`NodeNetwork` to resolve to member nodes.
- :func:`all_parents_present` — :data:`~roam_pub.validation.Validator` requiring all parent ids in a
  :data:`NodeNetwork` to resolve to member nodes.
- :func:`has_unique_ids` — :data:`~roam_pub.validation.Validator` requiring every
  :attr:`~roam_pub.roam_node.RoamNode.id` in a :data:`NodeNetwork` to be unique.
- :func:`is_acyclic` — :data:`~roam_pub.validation.Validator` requiring the child-edge graph of a
  :data:`NodeNetwork` to be cycle-free.
"""

from typing import Final

from roam_pub.roam_node import RoamNode
from roam_pub.roam_primitives import Id, Uid
from roam_pub.validation import ValidationError

type NodeNetwork = list[RoamNode]
"""A collection of :class:`~roam_pub.roam_node.RoamNode` instances.

Relationships between nodes are encoded via :attr:`~roam_pub.roam_node.RoamNode.children`,
:attr:`~roam_pub.roam_node.RoamNode.parents`, and :attr:`~roam_pub.roam_node.RoamNode.page` as
:class:`~roam_pub.roam_primitives.IdObject` stubs referencing :attr:`~roam_pub.roam_node.RoamNode.id`
values within the collection.
"""


def all_children_present(network: NodeNetwork) -> ValidationError | None:
    """Return ``None`` when every child id referenced in *network* resolves to a node in *network*.

    Iterates every node in *network* and checks that each :attr:`~roam_pub.roam_node.RoamNode.id`
    value found in a node's :attr:`~roam_pub.roam_node.RoamNode.children` list corresponds to the
    :attr:`~roam_pub.roam_node.RoamNode.id` of at least one node in *network*.

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


def all_parents_present(network: NodeNetwork, root_node: RoamNode) -> ValidationError | None:
    """Return ``None`` when every parent id referenced in *network* resolves to a node in *network*.

    Iterates every node in *network* and checks that each :attr:`~roam_pub.roam_node.RoamNode.id`
    value found in a node's :attr:`~roam_pub.roam_node.RoamNode.parents` list corresponds to the
    :attr:`~roam_pub.roam_node.RoamNode.id` of at least one node in *network*.  Parent ids that
    appear in *root_node*'s :attr:`~roam_pub.roam_node.RoamNode.parents` list are exempt from this
    check — they are considered external ancestors that legitimately live outside *network*.

    A network with no parents at all vacuously satisfies this condition and returns ``None``.

    Args:
        network: The collection of nodes to examine.
        root_node: The root of *network*.  Its parent ids are treated as external ancestors and
            exempt from the presence check.

    Returns:
        ``None`` if every applicable parent id in *network* resolves to a node in
        *network*; a :class:`~roam_pub.validation.ValidationError` listing the sorted
        absent parent ids and the sorted ids of the nodes that referenced them otherwise.
    """
    network_ids: Final[set[Id]] = {n.id for n in network}
    external_ancestor_ids: Final[set[Id]] = {p.id for p in (root_node.parents or [])}
    violations: Final[list[tuple[Id, Id]]] = [
        (n.id, parent.id)
        for n in network
        if n.parents
        for parent in n.parents
        if parent.id not in network_ids and parent.id not in external_ancestor_ids
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
    """Return ``None`` when every :attr:`~roam_pub.roam_node.RoamNode.id` in *network* is unique.

    Checks that no two nodes in *network* share the same :attr:`~roam_pub.roam_node.RoamNode.id`
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

    Performs a depth-first search over the :attr:`~roam_pub.roam_node.RoamNode.children` edges of
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
