"""Tests for the roam_node module."""

import pytest

from roam_pub.roam_node import (
    NodeNetwork,
    RoamNode,
    all_children_present,
    all_parents_present,
    has_single_root,
    has_unique_ids,
    is_acyclic,
    is_root,
)
from roam_pub.roam_primitives import IdObject
from roam_pub.validation import ValidationError

from conftest import STUB_TIME, STUB_USER


class TestIsRoot:
    """Tests for is_root."""

    # ------------------------------------------------------------------
    # parents=None / empty → always root
    # ------------------------------------------------------------------

    def test_none_parents_is_root(self) -> None:
        """Test that a node with parents=None is a root."""
        node = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        assert is_root(node, [node]) is True

    def test_empty_parents_is_root(self) -> None:
        """Test that a node with an empty parents list is a root."""
        node = RoamNode(
            uid="block0001", id=10, time=STUB_TIME, user=STUB_USER, string="stub", parents=[], page=IdObject(id=99)
        )
        assert is_root(node, [node]) is True

    # ------------------------------------------------------------------
    # parents non-empty but all absent from network → root
    # ------------------------------------------------------------------

    def test_node_with_absent_parent_is_root(self) -> None:
        """Test that a node whose single parent id is absent from the network is a root."""
        node = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
        )
        assert is_root(node, [node]) is True

    def test_node_with_all_parents_absent_is_root(self) -> None:
        """Test that a node with multiple parents all absent from the network is a root."""
        node = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=97), IdObject(id=98), IdObject(id=99)],
            page=IdObject(id=99),
        )
        assert is_root(node, [node]) is True

    def test_node_with_absent_parent_in_empty_network_is_root(self) -> None:
        """Test that a node with parents is a root when the network is empty (all parents absent)."""
        node = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        assert is_root(node, []) is True

    # ------------------------------------------------------------------
    # parents non-empty and at least one present in network → not root
    # ------------------------------------------------------------------

    def test_single_parent_in_network_is_not_root(self) -> None:
        """Test that a node whose single parent id is present in the network is not a root."""
        parent = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        assert is_root(child, [parent, child]) is False

    def test_all_parents_in_network_is_not_root(self) -> None:
        """Test that a node with every parent id present in the network is not a root."""
        parent1 = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        parent2 = RoamNode(uid="page00002", id=2, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1), IdObject(id=2)],
            page=IdObject(id=1),
        )
        assert is_root(child, [parent1, parent2, child]) is False

    def test_one_parent_in_network_among_several_is_not_root(self) -> None:
        """Test that a node is not a root when any one of its parents is in the network."""
        parent = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1), IdObject(id=99)],
            page=IdObject(id=1),
        )
        assert is_root(child, [parent, child]) is False

    # ------------------------------------------------------------------
    # two-node parent→child network: both nodes evaluated correctly
    # ------------------------------------------------------------------

    def test_parent_is_root_in_two_node_network(self) -> None:
        """Test that the parent node is identified as a root in a simple two-node network."""
        parent = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        network: NodeNetwork = [parent, child]
        assert is_root(parent, network) is True

    def test_child_is_not_root_in_two_node_network(self) -> None:
        """Test that the child node is not a root in a simple two-node network."""
        parent = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        network: NodeNetwork = [parent, child]
        assert is_root(child, network) is False


class TestHasSingleRoot:
    """Tests for has_single_root."""

    # ------------------------------------------------------------------
    # empty network → error
    # ------------------------------------------------------------------

    def test_empty_network_returns_error(self) -> None:
        """Test that an empty network has no root and returns a ValidationError."""
        assert has_single_root([]) == ValidationError(
            message="expected exactly one root node; found 0: []", validator=has_single_root
        )

    # ------------------------------------------------------------------
    # single-node networks
    # ------------------------------------------------------------------

    def test_single_parentless_node_returns_none(self) -> None:
        """Test that a one-node network whose node has no parents returns None."""
        node = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        assert has_single_root([node]) is None

    def test_single_node_with_absent_parent_returns_none(self) -> None:
        """Test that a one-node network whose parent is absent from the network is treated as a root."""
        node = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
        )
        assert has_single_root([node]) is None

    # ------------------------------------------------------------------
    # two-node networks
    # ------------------------------------------------------------------

    def test_parent_child_pair_returns_none(self) -> None:
        """Test that a two-node parent→child network has exactly one root and returns None."""
        parent = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        assert has_single_root([parent, child]) is None

    def test_two_parentless_nodes_returns_error(self) -> None:
        """Test that a network of two independent root nodes returns a ValidationError."""
        node1 = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        node2 = RoamNode(uid="page00002", id=2, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        assert has_single_root([node1, node2]) == ValidationError(
            message="expected exactly one root node; found 2: ['page00001', 'page00002']",
            validator=has_single_root,
        )

    def test_mutual_cycle_returns_error(self) -> None:
        """Test that a two-node cycle (each node lists the other as parent) returns a ValidationError."""
        node_a = RoamNode(
            uid="cycleA001",
            id=1,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=2)],
            page=IdObject(id=99),
        )
        node_b = RoamNode(
            uid="cycleB001",
            id=2,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=99),
        )
        assert has_single_root([node_a, node_b]) == ValidationError(
            message="expected exactly one root node; found 0: []",
            validator=has_single_root,
        )

    # ------------------------------------------------------------------
    # larger networks
    # ------------------------------------------------------------------

    def test_three_node_linear_chain_returns_none(self) -> None:
        """Test that a three-node linear chain has exactly one root and returns None."""
        root = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        mid = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        leaf = RoamNode(
            uid="block0002",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=10)],
            page=IdObject(id=1),
        )
        assert has_single_root([root, mid, leaf]) is None

    def test_two_independent_trees_returns_error(self) -> None:
        """Test that a network containing two separate rooted trees returns a ValidationError."""
        root1 = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        child1 = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        root2 = RoamNode(uid="page00002", id=2, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        child2 = RoamNode(
            uid="block0002",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=2)],
            page=IdObject(id=2),
        )
        assert has_single_root([root1, child1, root2, child2]) == ValidationError(
            message="expected exactly one root node; found 2: ['page00001', 'page00002']",
            validator=has_single_root,
        )


class TestAllChildrenPresent:
    """Tests for all_children_present."""

    # ------------------------------------------------------------------
    # trivially satisfied → None
    # ------------------------------------------------------------------

    def test_empty_network_returns_none(self) -> None:
        """Test that an empty network vacuously satisfies the condition and returns None."""
        assert all_children_present([]) is None

    def test_network_with_no_children_returns_none(self) -> None:
        """Test that a network of leaf nodes (all children=None) vacuously returns None."""
        node1 = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        node2 = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="text",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        assert all_children_present([node1, node2]) is None

    def test_node_with_empty_children_list_returns_none(self) -> None:
        """Test that a node with an empty children list vacuously returns None."""
        node = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        assert all_children_present([node]) is None

    # ------------------------------------------------------------------
    # all children present → None
    # ------------------------------------------------------------------

    def test_single_child_present_returns_none(self) -> None:
        """Test that a parent whose single child id is in the network returns None."""
        parent = RoamNode(
            uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=10)]
        )
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="text",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        assert all_children_present([parent, child]) is None

    def test_multiple_children_all_present_returns_none(self) -> None:
        """Test that a parent whose every child id is in the network returns None."""
        parent = RoamNode(
            uid="page00001",
            id=1,
            time=STUB_TIME,
            user=STUB_USER,
            title="stub",
            children=[IdObject(id=10), IdObject(id=20)],
        )
        child1 = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="c1",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        child2 = RoamNode(
            uid="block0002",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="c2",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        assert all_children_present([parent, child1, child2]) is None

    def test_multi_level_network_all_children_present_returns_none(self) -> None:
        """Test that a multi-level network with all children present at every level returns None."""
        root = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=10)])
        mid = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="mid",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
            children=[IdObject(id=20)],
        )
        leaf = RoamNode(
            uid="block0002",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="leaf",
            parents=[IdObject(id=10)],
            page=IdObject(id=1),
        )
        assert all_children_present([root, mid, leaf]) is None

    # ------------------------------------------------------------------
    # at least one child absent → ValidationError
    # ------------------------------------------------------------------

    def test_single_absent_child_returns_error(self) -> None:
        """Test that a node whose single child id is absent from the network returns a ValidationError."""
        parent = RoamNode(
            uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=99)]
        )
        assert all_children_present([parent]) == ValidationError(
            message="child ids absent from network: [99]; referenced by nodes: [1]",
            validator=all_children_present,
        )

    def test_one_absent_among_several_children_returns_error(self) -> None:
        """Test that a node with one absent child id among several returns a ValidationError."""
        parent = RoamNode(
            uid="page00001",
            id=1,
            time=STUB_TIME,
            user=STUB_USER,
            title="stub",
            children=[IdObject(id=10), IdObject(id=99)],
        )
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="text",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        assert all_children_present([parent, child]) == ValidationError(
            message="child ids absent from network: [99]; referenced by nodes: [1]",
            validator=all_children_present,
        )

    def test_absent_child_in_second_node_returns_error(self) -> None:
        """Test that a missing child in any node in the network returns a ValidationError."""
        root = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=10)])
        mid = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="mid",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
            children=[IdObject(id=99)],
        )
        assert all_children_present([root, mid]) == ValidationError(
            message="child ids absent from network: [99]; referenced by nodes: [10]",
            validator=all_children_present,
        )


class TestAllParentsPresent:
    """Tests for all_parents_present."""

    # ------------------------------------------------------------------
    # trivially satisfied → None
    # ------------------------------------------------------------------

    def test_empty_network_returns_none(self) -> None:
        """Test that an empty network vacuously satisfies the condition and returns None."""
        assert all_parents_present([]) is None

    def test_network_with_no_parents_returns_none(self) -> None:
        """Test that a network of root nodes (all parents=None) vacuously returns None."""
        node1 = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        node2 = RoamNode(uid="page00002", id=2, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        assert all_parents_present([node1, node2]) is None

    def test_node_with_empty_parents_list_returns_none(self) -> None:
        """Test that a node with an empty parents list vacuously returns None."""
        node = RoamNode(
            uid="block0001", id=10, time=STUB_TIME, user=STUB_USER, string="stub", parents=[], page=IdObject(id=99)
        )
        assert all_parents_present([node]) is None

    # ------------------------------------------------------------------
    # all parents present → None
    # ------------------------------------------------------------------

    def test_single_parent_present_returns_none(self) -> None:
        """Test that a child whose single parent id is in the network returns None."""
        parent = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        assert all_parents_present([parent, child]) is None

    def test_multi_level_network_all_parents_present_returns_none(self) -> None:
        """Test that a multi-level network with all parents present at every level returns None."""
        root = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        mid = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="mid",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        leaf = RoamNode(
            uid="block0002",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="leaf",
            parents=[IdObject(id=10)],
            page=IdObject(id=1),
        )
        assert all_parents_present([root, mid, leaf]) is None

    # ------------------------------------------------------------------
    # at least one parent absent → ValidationError
    # ------------------------------------------------------------------

    def test_single_absent_parent_returns_error(self) -> None:
        """Test that a node whose single parent id is absent from the network returns a ValidationError."""
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
        )
        assert all_parents_present([child]) == ValidationError(
            message="parent ids absent from network: [99]; referenced by nodes: [10]",
            validator=all_parents_present,
        )

    def test_one_absent_among_several_parents_returns_error(self) -> None:
        """Test that a node with one absent parent id among several returns a ValidationError."""
        parent = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1), IdObject(id=99)],
            page=IdObject(id=1),
        )
        assert all_parents_present([parent, child]) == ValidationError(
            message="parent ids absent from network: [99]; referenced by nodes: [10]",
            validator=all_parents_present,
        )

    def test_absent_parent_in_second_node_returns_error(self) -> None:
        """Test that a missing parent in any node in the network returns a ValidationError."""
        root = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        mid = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="mid",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        leaf = RoamNode(
            uid="block0002",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="leaf",
            parents=[IdObject(id=99)],
            page=IdObject(id=1),
        )
        assert all_parents_present([root, mid, leaf]) == ValidationError(
            message="parent ids absent from network: [99]; referenced by nodes: [20]",
            validator=all_parents_present,
        )

    # ------------------------------------------------------------------
    # is_standalone=False — external ancestors exempt from parent-presence check
    # ------------------------------------------------------------------

    def test_not_rooted_root_with_absent_parent_returns_none(self) -> None:
        """Test that is_standalone=False exempts a root node whose parent is absent from the network."""
        # root has parents=[id=99] absent from network; with is_standalone=False it is exempt
        root = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
        )
        assert all_parents_present([root], is_standalone=False) is None

    def test_not_rooted_external_ancestor_in_non_root_parents_returns_none(self) -> None:
        """Test that external ancestors propagate: a non-root node's parents list may include external ancestor ids.

        Because RoamNode.parents holds the complete ancestor path (not just the immediate parent),
        a non-root node in a sub-network will carry external ancestor ids in its parents list — the
        same ids that appear in the effective root's parents.  These must be exempt from the check.
        """
        # Absolute graph: A(id=99) → B(id=10) → C(id=20); sub-network is [B, C].
        # B is the effective root; A is an external ancestor.
        # C.parents = [A=99, B=10] — the full ancestor path; 99 is external and must be exempt.
        root = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
        )
        child = RoamNode(
            uid="block0002",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=99), IdObject(id=10)],
            page=IdObject(id=99),
        )
        assert all_parents_present([root, child], is_standalone=False) is None

    def test_not_rooted_non_root_with_absent_parent_returns_error(self) -> None:
        """Test that is_standalone=False still catches absent parents on non-root nodes."""
        # page is a root (no parents); child has parents=[id=page, id=99] where 99 is absent
        page = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1), IdObject(id=99)],
            page=IdObject(id=1),
        )
        assert all_parents_present([page, child], is_standalone=False) == ValidationError(
            message="parent ids absent from network: [99]; referenced by nodes: [10]",
            validator=all_parents_present,
        )

    def test_not_rooted_subtree_with_external_root_parent_returns_none(self) -> None:
        """Test is_standalone=False on a subtree: root's external parent is ignored; child's present parent is valid."""
        # Simulates a node-UID fetch: root's parent (id=99) lives outside the network
        root = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="root",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
        )
        child = RoamNode(
            uid="block0002",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="child",
            parents=[IdObject(id=10)],
            page=IdObject(id=99),
        )
        assert all_parents_present([root, child], is_standalone=False) is None

    def test_not_rooted_true_is_default_behavior(self) -> None:
        """Test that omitting is_standalone behaves identically to is_standalone=True."""
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
        )
        assert all_parents_present([child]) == all_parents_present([child], is_standalone=True)


class TestHasUniqueIds:
    """Tests for has_unique_ids."""

    # ------------------------------------------------------------------
    # trivially satisfied → None
    # ------------------------------------------------------------------

    def test_empty_network_returns_none(self) -> None:
        """Test that an empty network vacuously satisfies the condition and returns None."""
        assert has_unique_ids([]) is None

    def test_single_node_returns_none(self) -> None:
        """Test that a one-node network trivially has unique ids and returns None."""
        node = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        assert has_unique_ids([node]) is None

    # ------------------------------------------------------------------
    # all ids distinct → None
    # ------------------------------------------------------------------

    def test_two_nodes_with_distinct_ids_returns_none(self) -> None:
        """Test that a two-node network with distinct ids returns None."""
        node1 = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        node2 = RoamNode(uid="page00002", id=2, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        assert has_unique_ids([node1, node2]) is None

    def test_three_nodes_with_distinct_ids_returns_none(self) -> None:
        """Test that a three-node network with all distinct ids returns None."""
        node1 = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        node2 = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="text",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        node3 = RoamNode(
            uid="block0002",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="text",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        assert has_unique_ids([node1, node2, node3]) is None

    # ------------------------------------------------------------------
    # at least one duplicate id → ValidationError
    # ------------------------------------------------------------------

    def test_two_nodes_with_same_id_returns_error(self) -> None:
        """Test that a two-node network where both nodes share the same id returns a ValidationError."""
        node1 = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        node2 = RoamNode(uid="page00002", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        assert has_unique_ids([node1, node2]) == ValidationError(
            message="expected unique node ids; found duplicates: [1]",
            validator=has_unique_ids,
        )

    def test_one_duplicate_among_several_nodes_returns_error(self) -> None:
        """Test that a single duplicate id among otherwise distinct ids returns a ValidationError."""
        node1 = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        node2 = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="a",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        node3 = RoamNode(
            uid="block0002",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="b",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        assert has_unique_ids([node1, node2, node3]) == ValidationError(
            message="expected unique node ids; found duplicates: [10]",
            validator=has_unique_ids,
        )


class TestIsAcyclic:
    """Tests for is_acyclic."""

    # ------------------------------------------------------------------
    # trivially satisfied → None
    # ------------------------------------------------------------------

    def test_empty_network_returns_none(self) -> None:
        """Test that an empty network vacuously satisfies the condition and returns None."""
        assert is_acyclic([]) is None

    def test_single_node_no_children_returns_none(self) -> None:
        """Test that a single node with no children has no cycle and returns None."""
        node = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        assert is_acyclic([node]) is None

    def test_single_node_empty_children_returns_none(self) -> None:
        """Test that a single node with an empty children list has no cycle and returns None."""
        node = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        assert is_acyclic([node]) is None

    # ------------------------------------------------------------------
    # acyclic networks → None
    # ------------------------------------------------------------------

    def test_two_node_chain_returns_none(self) -> None:
        """Test that a two-node parent→child chain has no cycle and returns None."""
        parent = RoamNode(
            uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=10)]
        )
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        assert is_acyclic([parent, child]) is None

    def test_three_node_chain_returns_none(self) -> None:
        """Test that a three-node linear chain has no cycle and returns None."""
        root = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=10)])
        mid = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
            children=[IdObject(id=20)],
        )
        leaf = RoamNode(
            uid="block0002",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=10)],
            page=IdObject(id=1),
        )
        assert is_acyclic([root, mid, leaf]) is None

    def test_branching_tree_returns_none(self) -> None:
        """Test that a root with two children (no cross-edges) has no cycle and returns None."""
        root = RoamNode(
            uid="page00001",
            id=1,
            time=STUB_TIME,
            user=STUB_USER,
            title="stub",
            children=[IdObject(id=10), IdObject(id=20)],
        )
        child1 = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        child2 = RoamNode(
            uid="block0002",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        assert is_acyclic([root, child1, child2]) is None

    def test_child_outside_network_is_skipped_returns_none(self) -> None:
        """Test that a child reference outside the network is silently skipped and returns None."""
        node = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=99)])
        assert is_acyclic([node]) is None

    # ------------------------------------------------------------------
    # cyclic networks → ValidationError
    # ------------------------------------------------------------------

    def test_self_loop_returns_error(self) -> None:
        """Test that a node whose children list references itself returns a ValidationError."""
        node = RoamNode(uid="cycleA001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=1)])
        assert is_acyclic([node]) == ValidationError(
            message="child-edge graph contains a directed cycle involving node 'cycleA001'",
            validator=is_acyclic,
        )

    def test_two_node_mutual_cycle_returns_error(self) -> None:
        """Test that a two-node cycle (A→B→A via children) returns a ValidationError."""
        node_a = RoamNode(
            uid="cycleA001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=2)]
        )
        node_b = RoamNode(
            uid="cycleB001", id=2, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=1)]
        )
        assert is_acyclic([node_a, node_b]) == ValidationError(
            message="child-edge graph contains a directed cycle involving node 'cycleA001'",
            validator=is_acyclic,
        )

    def test_three_node_cycle_returns_error(self) -> None:
        """Test that a three-node cycle (A→B→C→A via children) returns a ValidationError."""
        node_a = RoamNode(
            uid="cycleA001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=2)]
        )
        node_b = RoamNode(
            uid="cycleB001", id=2, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=3)]
        )
        node_c = RoamNode(
            uid="cycleC001", id=3, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=1)]
        )
        assert is_acyclic([node_a, node_b, node_c]) == ValidationError(
            message="child-edge graph contains a directed cycle involving node 'cycleA001'",
            validator=is_acyclic,
        )


class TestRoamNodeProps:
    """Tests for the RoamNode.props field (block properties / :block/props)."""

    def test_props_defaults_to_none(self) -> None:
        """Test that props is None when not supplied."""
        node = RoamNode(
            uid="block0001",
            id=1,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
        )
        assert node.props is None

    def test_props_accepts_string_values(self) -> None:
        """Test that props stores a string-valued block property map."""
        node = RoamNode(
            uid="block0001",
            id=1,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
            props={"ah-level": "h4"},
        )
        assert node.props == {"ah-level": "h4"}

    def test_props_accepts_multiple_entries(self) -> None:
        """Test that props can hold multiple block property entries."""
        node = RoamNode(
            uid="block0001",
            id=1,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
            props={"ah-level": "h5", ":some-other": "value"},
        )
        assert node.props is not None
        assert node.props["ah-level"] == "h5"
        assert node.props[":some-other"] == "value"

    def test_props_round_trips_through_model_validate(self) -> None:
        """Test that props survives a model_validate round-trip from a raw dict."""
        raw: dict[str, object] = {
            "uid": "block0001",
            "id": 1,
            "time": STUB_TIME,
            "user": {"id": 1},
            "string": "stub",
            "parents": [{"id": 99}],
            "page": {"id": 99},
            "props": {"ah-level": "h6"},
        }
        node = RoamNode.model_validate(raw)
        assert node.props == {"ah-level": "h6"}

    def test_props_none_round_trips_through_model_validate(self) -> None:
        """Test that a missing props key in raw dict produces props=None."""
        raw: dict[str, object] = {
            "uid": "block0001",
            "id": 1,
            "time": STUB_TIME,
            "user": {"id": 1},
            "string": "stub",
            "parents": [{"id": 99}],
            "page": {"id": 99},
        }
        node = RoamNode.model_validate(raw)
        assert node.props is None

    def test_node_with_props_is_frozen(self) -> None:
        """Test that a node with props set is immutable."""
        node = RoamNode(
            uid="block0001",
            id=1,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
            props={"ah-level": "h4"},
        )
        with pytest.raises(Exception):
            node.props = None  # type: ignore[misc]
