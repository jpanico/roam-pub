"""Tests for the roam_network module."""

from roam_pub.roam_network import (
    all_children_present,
    all_parents_present,
    has_unique_ids,
    is_acyclic,
)
from roam_pub.roam_node import RoamNode
from roam_pub.roam_primitives import IdObject
from roam_pub.validation import ValidationError

from conftest import STUB_TIME, STUB_USER


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
        stub = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        assert all_parents_present([], stub) is None

    def test_network_with_no_parents_returns_none(self) -> None:
        """Test that a network of root nodes (all parents=None) vacuously returns None."""
        node1 = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        node2 = RoamNode(uid="page00002", id=2, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        assert all_parents_present([node1, node2], node1) is None

    def test_node_with_empty_parents_list_returns_none(self) -> None:
        """Test that a node with an empty parents list vacuously returns None."""
        node = RoamNode(
            uid="block0001", id=10, time=STUB_TIME, user=STUB_USER, string="stub", parents=[], page=IdObject(id=99)
        )
        assert all_parents_present([node], node) is None

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
        assert all_parents_present([parent, child], parent) is None

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
        assert all_parents_present([root, mid, leaf], root) is None

    # ------------------------------------------------------------------
    # at least one parent absent → ValidationError
    # ------------------------------------------------------------------

    def test_single_absent_parent_returns_error(self) -> None:
        """Test that a non-root node whose single parent id is absent from the network returns a ValidationError."""
        root = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
        )
        assert all_parents_present([root, child], root) == ValidationError(
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
        assert all_parents_present([parent, child], parent) == ValidationError(
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
        assert all_parents_present([root, mid, leaf], root) == ValidationError(
            message="parent ids absent from network: [99]; referenced by nodes: [20]",
            validator=all_parents_present,
        )

    # ------------------------------------------------------------------
    # root's external parents exempt from parent-presence check
    # ------------------------------------------------------------------

    def test_root_with_absent_parent_returns_none(self) -> None:
        """Test that a root node's absent parent is exempt from the check."""
        root = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
        )
        assert all_parents_present([root], root) is None

    def test_external_ancestor_in_non_root_parents_returns_none(self) -> None:
        """Test that external ancestors propagate: a non-root node's parents list may include external ancestor ids.

        Because RoamNode.parents holds the complete ancestor path (not just the immediate parent),
        a non-root node in a sub-network will carry external ancestor ids in its parents list — the
        same ids that appear in the root's parents.  These must be exempt from the check.
        """
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
        assert all_parents_present([root, child], root) is None

    def test_non_root_with_absent_parent_returns_error(self) -> None:
        """Test that only root's external parents are exempt — absent parents on non-root nodes are still caught."""
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
        assert all_parents_present([page, child], page) == ValidationError(
            message="parent ids absent from network: [99]; referenced by nodes: [10]",
            validator=all_parents_present,
        )

    def test_subtree_with_external_root_parent_returns_none(self) -> None:
        """Test a subtree: root's external parent is exempt; child's present parent is valid."""
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
        assert all_parents_present([root, child], root) is None


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
