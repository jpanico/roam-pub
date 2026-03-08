"""Tests for the roam_tree module."""

import pytest

from roam_pub.roam_network import (
    all_children_present,
    has_unique_ids,
    is_acyclic,
)
from roam_pub.roam_node import RoamNode
from roam_pub.roam_primitives import Id, IdObject
from roam_pub.roam_tree import NodeTree, NodeTreeDFSIterator, is_tree
from roam_pub.validation import ValidationError

from conftest import STUB_TIME, STUB_USER, article0_node_tree


class TestIsTree:
    """Tests for is_tree."""

    # ------------------------------------------------------------------
    # valid trees → ValidationResult with no errors
    # ------------------------------------------------------------------

    def test_empty_network_returns_valid(self) -> None:
        """Test that an empty network satisfies all remaining tree invariants."""
        result = is_tree([])
        assert result.is_valid is True

    def test_single_root_node_is_valid(self) -> None:
        """Test that a single parentless node satisfies all tree invariants."""
        node = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        result = is_tree([node])
        assert result.is_valid is True

    def test_two_node_tree_is_valid(self) -> None:
        """Test that a proper root→child pair satisfies all tree invariants."""
        root = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=10)])
        child = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        result = is_tree([root, child])
        assert result.is_valid is True

    def test_three_node_chain_is_valid(self) -> None:
        """Test that a three-node linear chain satisfies all tree invariants."""
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
        result = is_tree([root, mid, leaf])
        assert result.is_valid is True

    # ------------------------------------------------------------------
    # invalid trees → ValidationResult with errors
    # ------------------------------------------------------------------

    def test_self_loop_returns_invalid(self) -> None:
        """Test that a self-loop violates is_acyclic and returns an invalid result."""
        node = RoamNode(uid="cycleA001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=1)])
        result = is_tree([node])
        assert result.is_valid is False
        assert result.errors == (
            ValidationError(
                message="child-edge graph contains a directed cycle involving node 'cycleA001'",
                validator=is_acyclic,
            ),
        )

    def test_missing_child_returns_invalid(self) -> None:
        """Test that an absent child reference violates all_children_present and returns an invalid result."""
        parent = RoamNode(
            uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=99)]
        )
        result = is_tree([parent])
        assert result.is_valid is False
        assert result.errors == (
            ValidationError(
                message="child ids absent from network: [99]; referenced by nodes: [1]",
                validator=all_children_present,
            ),
        )

    def test_two_roots_returns_valid(self) -> None:
        """Test that two parentless nodes satisfy all tree invariants."""
        node1 = RoamNode(uid="page00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        node2 = RoamNode(uid="page00002", id=2, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        result = is_tree([node1, node2])
        assert result.is_valid is True

    def test_multiple_failures_accumulate_all_errors(self) -> None:
        """Test that all validators run even after prior failures, accumulating every error."""
        # duplicate id=1 → has_unique_ids fails
        # node1 references absent child id=99 → all_children_present fails
        node1 = RoamNode(
            uid="page00001",
            id=1,
            time=STUB_TIME,
            user=STUB_USER,
            title="stub",
            children=[IdObject(id=99)],
        )
        node2 = RoamNode(
            uid="page00002",
            id=1,
            time=STUB_TIME,
            user=STUB_USER,
            string="stub",
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        result = is_tree([node1, node2])
        assert result.is_valid is False
        assert result.errors == (
            ValidationError(message="expected unique node ids; found duplicates: [1]", validator=has_unique_ids),
            ValidationError(
                message="child ids absent from network: [99]; referenced by nodes: [1]",
                validator=all_children_present,
            ),
        )

    def test_not_rooted_subtree_is_valid(self) -> None:
        """Test that a node-UID subtree with an external root parent is valid."""
        # root's parent (id=99) is outside the network — is_tree checks only structural invariants
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
            children=[],
        )
        result = is_tree([root, child])
        assert result.is_valid is True

    def test_subtree_root_external_parent_is_always_exempt(self) -> None:
        """Test that a subtree root's external parent is always exempt — no flag required."""
        root = RoamNode(
            uid="block0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="root",
            parents=[IdObject(id=99)],
            page=IdObject(id=99),
        )
        result = is_tree([root])
        assert result.is_valid is True


class TestNodeTree:
    """Tests for NodeTree."""

    def test_article_fixture_is_valid_tree(self) -> None:
        """Test that test_article_0_nodes.yaml constructs a valid NodeTree without raising."""
        node_tree = article0_node_tree()
        assert node_tree.network


# ---------------------------------------------------------------------------
# TestNodeTreeDFSIterator
# ---------------------------------------------------------------------------


class TestNodeTreeDFSIterator:
    """Tests for NodeTreeDFSIterator — pre-order depth-first traversal of a NodeTree."""

    def test_single_node_tree_yields_root(self) -> None:
        """Test that a one-node tree yields only the root node."""
        root = RoamNode(uid="root00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        tree = NodeTree(network=[root], root_node=root)
        assert [n.uid for n in NodeTreeDFSIterator(tree)] == ["root00001"]

    def test_two_node_tree_yields_root_then_child(self) -> None:
        """Test that a root→child tree yields root first, then child."""
        root = RoamNode(uid="root00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[IdObject(id=10)])
        child = RoamNode(
            uid="chld00001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="c",
            order=0,
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        tree = NodeTree(network=[root, child], root_node=root)
        assert [n.uid for n in NodeTreeDFSIterator(tree)] == ["root00001", "chld00001"]

    def test_children_yielded_in_ascending_order_field(self) -> None:
        """Test that children are visited in ascending order-field order, not id order."""
        root = RoamNode(
            uid="root00001",
            id=1,
            time=STUB_TIME,
            user=STUB_USER,
            title="stub",
            children=[IdObject(id=10), IdObject(id=20)],
        )
        # id=20 has order=0 so it should come first despite having the larger id
        child_first = RoamNode(
            uid="chld00002",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="first",
            order=0,
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        child_second = RoamNode(
            uid="chld00001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="second",
            order=1,
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        tree = NodeTree(network=[root, child_first, child_second], root_node=root)
        assert [n.uid for n in NodeTreeDFSIterator(tree)] == ["root00001", "chld00002", "chld00001"]

    def test_preorder_visits_subtree_before_sibling(self) -> None:
        """Test that a child's full subtree is visited before the next sibling (pre-order)."""
        root = RoamNode(
            uid="root00001",
            id=1,
            time=STUB_TIME,
            user=STUB_USER,
            title="stub",
            children=[IdObject(id=10), IdObject(id=20)],
        )
        node_a = RoamNode(
            uid="nodeA0001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="A",
            order=0,
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
            children=[IdObject(id=11)],
        )
        node_a1 = RoamNode(
            uid="nodeA1001",
            id=11,
            time=STUB_TIME,
            user=STUB_USER,
            string="A1",
            order=0,
            parents=[IdObject(id=10)],
            page=IdObject(id=1),
        )
        node_b = RoamNode(
            uid="nodeB0001",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="B",
            order=1,
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        tree = NodeTree(network=[root, node_a, node_a1, node_b], root_node=root)
        assert [n.uid for n in NodeTreeDFSIterator(tree)] == ["root00001", "nodeA0001", "nodeA1001", "nodeB0001"]

    def test_all_nodes_yielded_exactly_once(self) -> None:
        """Test that every node in the tree is yielded exactly once with no duplicates."""
        root = RoamNode(
            uid="root00001",
            id=1,
            time=STUB_TIME,
            user=STUB_USER,
            title="stub",
            children=[IdObject(id=10), IdObject(id=20)],
        )
        child_a = RoamNode(
            uid="chld00001",
            id=10,
            time=STUB_TIME,
            user=STUB_USER,
            string="a",
            order=0,
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        child_b = RoamNode(
            uid="chld00002",
            id=20,
            time=STUB_TIME,
            user=STUB_USER,
            string="b",
            order=1,
            parents=[IdObject(id=1)],
            page=IdObject(id=1),
        )
        tree = NodeTree(network=[root, child_a, child_b], root_node=root)
        yielded: list[RoamNode] = list(NodeTreeDFSIterator(tree))
        assert len(yielded) == 3
        assert len({n.uid for n in yielded}) == 3

    def test_iterator_exhausted_raises_stop_iteration(self) -> None:
        """Test that __next__ raises StopIteration once all nodes have been yielded."""
        root = RoamNode(uid="root00001", id=1, time=STUB_TIME, user=STUB_USER, title="stub", children=[])
        tree = NodeTree(network=[root], root_node=root)
        it: NodeTreeDFSIterator = NodeTreeDFSIterator(tree)
        assert next(it).uid == "root00001"
        with pytest.raises(StopIteration):
            next(it)

    def test_article_fixture_yields_all_nodes(self) -> None:
        """Test that the iterator yields every node in the article fixture exactly once."""
        tree = article0_node_tree()
        yielded: list[RoamNode] = list(NodeTreeDFSIterator(tree))
        assert len(yielded) == len(tree.network)
        assert {n.uid for n in yielded} == {n.uid for n in tree.network}

    def test_article_fixture_parent_always_precedes_children(self) -> None:
        """Test that every parent node appears before all of its children in the traversal."""
        tree = article0_node_tree()
        id_map: dict[Id, RoamNode] = {n.id: n for n in tree.network}
        yielded: list[RoamNode] = list(NodeTreeDFSIterator(tree))
        position: dict[str, int] = {n.uid: i for i, n in enumerate(yielded)}
        for node in tree.network:
            if node.children:
                for child_stub in node.children:
                    child: RoamNode = id_map[child_stub.id]
                    assert position[node.uid] < position[child.uid]

    def test_article_fixture_dfs_id_order(self) -> None:
        """Test the exact pre-order DFS id sequence for the test_article fixture.

        Expected traversal (by Datomic entity id):
          3327  — root page "Test Article"
          3328  — Section 1         (order=0, child of root)
          3331  — Section 1.1       (order=0, child of 3328)
          3334  — illustration 1.1  (order=0, child of 3331)
          3336  — image block       (order=0, child of 3334)
          4029  — AI assistant text (order=1, child of 3328)
          3329  — Section 2         (order=1, child of root)
          3332  — Section 2.1       (order=0, child of 3329)
          4025  — Section 2.1.1     (order=0, child of 3332)
          4028  — Section 2.1.1.1   (order=0, child of 4025)
          4026  — Section 2.1.2     (order=1, child of 3329)
          3330  — Section 3         (order=2, child of root)
          3333  — Section 3.1       (order=0, child of 3330)
        """
        tree = article0_node_tree()
        expected_ids: list[Id] = [3327, 3328, 3331, 3334, 3336, 4029, 3329, 3332, 4025, 4028, 4026, 3330, 3333]
        assert [n.id for n in NodeTreeDFSIterator(tree)] == expected_ids
