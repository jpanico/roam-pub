"""Tests for the roam_node module."""

import pytest
from pydantic import ValidationError

from roam_pub.roam_node import NodeNetwork, RoamNode, is_root
from roam_pub.roam_types import IdObject

# Minimal required fields that are irrelevant to is_root logic.
_TIME = 0
_USER = IdObject(id=1)


class TestIsRoot:
    """Tests for is_root."""

    # ------------------------------------------------------------------
    # parents=None / empty → always root
    # ------------------------------------------------------------------

    def test_none_parents_is_root(self) -> None:
        """Test that a node with parents=None is a root."""
        node = RoamNode(uid="page00001", id=1, time=_TIME, user=_USER)
        assert is_root(node, [node]) is True

    def test_empty_parents_is_root(self) -> None:
        """Test that a node with an empty parents list is a root."""
        node = RoamNode(uid="page00001", id=1, time=_TIME, user=_USER, parents=[])
        assert is_root(node, [node]) is True

    # ------------------------------------------------------------------
    # parents exist but none of their ids are in network → root
    # ------------------------------------------------------------------

    def test_parent_id_absent_from_network_is_root(self) -> None:
        """Test that a node whose single parent id is absent from the network is a root."""
        node = RoamNode(uid="block0001", id=10, time=_TIME, user=_USER, parents=[IdObject(id=99)])
        assert is_root(node, [node]) is True

    def test_all_parent_ids_absent_from_network_is_root(self) -> None:
        """Test that a node whose every parent id is absent from the network is a root."""
        node = RoamNode(
            uid="block0001",
            id=10,
            time=_TIME,
            user=_USER,
            parents=[IdObject(id=97), IdObject(id=98), IdObject(id=99)],
        )
        assert is_root(node, [node]) is True

    def test_empty_network_with_parentless_node_is_root(self) -> None:
        """Test that a parentless node is a root even in an empty network."""
        node = RoamNode(uid="page00001", id=1, time=_TIME, user=_USER)
        assert is_root(node, []) is True

    def test_empty_network_with_parented_node_is_root(self) -> None:
        """Test that a node with parents is still a root when the network is empty."""
        node = RoamNode(uid="block0001", id=10, time=_TIME, user=_USER, parents=[IdObject(id=1)])
        assert is_root(node, []) is True

    # ------------------------------------------------------------------
    # at least one parent id is in network → not root
    # ------------------------------------------------------------------

    def test_single_parent_in_network_is_not_root(self) -> None:
        """Test that a node whose single parent id is present in the network is not a root."""
        parent = RoamNode(uid="page00001", id=1, time=_TIME, user=_USER)
        child = RoamNode(uid="block0001", id=10, time=_TIME, user=_USER, parents=[IdObject(id=1)])
        assert is_root(child, [parent, child]) is False

    def test_all_parents_in_network_is_not_root(self) -> None:
        """Test that a node with every parent id present in the network is not a root."""
        parent1 = RoamNode(uid="page00001", id=1, time=_TIME, user=_USER)
        parent2 = RoamNode(uid="page00002", id=2, time=_TIME, user=_USER)
        child = RoamNode(
            uid="block0001",
            id=10,
            time=_TIME,
            user=_USER,
            parents=[IdObject(id=1), IdObject(id=2)],
        )
        assert is_root(child, [parent1, parent2, child]) is False

    def test_one_parent_in_network_among_several_is_not_root(self) -> None:
        """Test that a node is not a root when any one of its parents is in the network."""
        parent = RoamNode(uid="page00001", id=1, time=_TIME, user=_USER)
        child = RoamNode(
            uid="block0001",
            id=10,
            time=_TIME,
            user=_USER,
            parents=[IdObject(id=1), IdObject(id=99)],
        )
        # id=99 is absent, but id=1 is present → not a root
        assert is_root(child, [parent, child]) is False

    # ------------------------------------------------------------------
    # two-node parent→child network: both nodes evaluated correctly
    # ------------------------------------------------------------------

    def test_parent_is_root_in_two_node_network(self) -> None:
        """Test that the parent node is identified as a root in a simple two-node network."""
        parent = RoamNode(uid="page00001", id=1, time=_TIME, user=_USER)
        child = RoamNode(uid="block0001", id=10, time=_TIME, user=_USER, parents=[IdObject(id=1)])
        network: NodeNetwork = [parent, child]
        assert is_root(parent, network) is True

    def test_child_is_not_root_in_two_node_network(self) -> None:
        """Test that the child node is not a root in a simple two-node network."""
        parent = RoamNode(uid="page00001", id=1, time=_TIME, user=_USER)
        child = RoamNode(uid="block0001", id=10, time=_TIME, user=_USER, parents=[IdObject(id=1)])
        network: NodeNetwork = [parent, child]
        assert is_root(child, network) is False


class TestRoamNodeProps:
    """Tests for the RoamNode.props field (block properties / :block/props)."""

    def test_props_defaults_to_none(self) -> None:
        """Test that props is None when not supplied."""
        node = RoamNode(uid="block0001", id=1, time=_TIME, user=_USER)
        assert node.props is None

    def test_props_accepts_string_values(self) -> None:
        """Test that props stores a string-valued block property map."""
        node = RoamNode(
            uid="block0001",
            id=1,
            time=_TIME,
            user=_USER,
            props={"ah-level": "h4"},
        )
        assert node.props == {"ah-level": "h4"}

    def test_props_accepts_multiple_entries(self) -> None:
        """Test that props can hold multiple block property entries."""
        node = RoamNode(
            uid="block0001",
            id=1,
            time=_TIME,
            user=_USER,
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
            "time": _TIME,
            "user": {"id": 1},
            "props": {"ah-level": "h6"},
        }
        node = RoamNode.model_validate(raw)
        assert node.props == {"ah-level": "h6"}

    def test_props_none_round_trips_through_model_validate(self) -> None:
        """Test that a missing props key in raw dict produces props=None."""
        raw: dict[str, object] = {
            "uid": "block0001",
            "id": 1,
            "time": _TIME,
            "user": {"id": 1},
        }
        node = RoamNode.model_validate(raw)
        assert node.props is None

    def test_node_with_props_is_frozen(self) -> None:
        """Test that a node with props set is immutable."""
        node = RoamNode(uid="block0001", id=1, time=_TIME, user=_USER, props={"ah-level": "h4"})
        with pytest.raises(Exception):
            node.props = None  # type: ignore[misc]
