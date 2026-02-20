"""Tests for the roam_transcribe module."""

import json
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from roam_pub.roam_model import IdObject, RoamNode
from roam_pub.roam_transcribe import pull_block_to_roam_node

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "json"


def load_pull_block() -> dict:
    """Load the single pull block from the output.json fixture."""
    with open(FIXTURES_DIR / "output.json") as f:
        data = json.load(f)
    return data["result"][0][0]


class TestPullBlockToRoamNode:
    """Tests for pull_block_to_roam_node."""

    def test_returns_roam_node(self) -> None:
        """Test that a valid pull block produces a RoamNode."""
        node = pull_block_to_roam_node(load_pull_block())
        assert isinstance(node, RoamNode)

    def test_uid(self) -> None:
        """Test that uid is correctly mapped."""
        node = pull_block_to_roam_node(load_pull_block())
        assert node.uid == "XO4nOy4D6"

    def test_id(self) -> None:
        """Test that id is correctly mapped."""
        node = pull_block_to_roam_node(load_pull_block())
        assert node.id == 2370

    def test_title(self) -> None:
        """Test that title is correctly mapped."""
        node = pull_block_to_roam_node(load_pull_block())
        assert node.title == "[[Illustration]] Brief"

    def test_time(self) -> None:
        """Test that time is correctly mapped."""
        node = pull_block_to_roam_node(load_pull_block())
        assert node.time == 1764876416940

    def test_sidebar(self) -> None:
        """Test that sidebar is correctly mapped."""
        node = pull_block_to_roam_node(load_pull_block())
        assert node.sidebar == 16

    def test_user_is_id_object(self) -> None:
        """Test that user is coerced into an IdObject."""
        node = pull_block_to_roam_node(load_pull_block())
        assert isinstance(node.user, IdObject)
        assert node.user.id == 3

    def test_children_are_id_objects(self) -> None:
        """Test that children are coerced into a list of IdObjects."""
        node = pull_block_to_roam_node(load_pull_block())
        assert node.children is not None
        assert len(node.children) == 3
        assert all(isinstance(c, IdObject) for c in node.children)
        assert [c.id for c in node.children] == [2371, 2396, 2430]

    def test_refs_are_id_objects(self) -> None:
        """Test that refs are coerced into a list of IdObjects."""
        node = pull_block_to_roam_node(load_pull_block())
        assert node.refs is not None
        assert len(node.refs) == 1
        assert isinstance(node.refs[0], IdObject)
        assert node.refs[0].id == 2459

    def test_block_only_fields_are_none(self) -> None:
        """Test that block-only fields absent from this page node are None."""
        node = pull_block_to_roam_node(load_pull_block())
        assert node.string is None
        assert node.order is None
        assert node.heading is None
        assert node.page is None
        assert node.open is None
        assert node.parents is None

    def test_sparse_fields_are_none(self) -> None:
        """Test that sparse metadata fields absent from this node are None."""
        node = pull_block_to_roam_node(load_pull_block())
        assert node.attrs is None
        assert node.lookup is None
        assert node.seen_by is None

    def test_unknown_keys_are_ignored(self) -> None:
        """Test that unknown keys such as 'prevent-clean' are silently ignored."""
        pull_block = load_pull_block()
        assert "prevent-clean" in pull_block  # confirm fixture has the key
        node = pull_block_to_roam_node(pull_block)
        assert not hasattr(node, "prevent_clean")

    def test_missing_uid_raises_validation_error(self) -> None:
        """Test that a pull block missing 'uid' raises ValidationError."""
        pull_block = load_pull_block()
        del pull_block["uid"]
        with pytest.raises(ValidationError):
            pull_block_to_roam_node(pull_block)

    def test_missing_id_raises_validation_error(self) -> None:
        """Test that a pull block missing 'id' raises ValidationError."""
        pull_block = load_pull_block()
        del pull_block["id"]
        with pytest.raises(ValidationError):
            pull_block_to_roam_node(pull_block)

    def test_node_is_immutable(self) -> None:
        """Test that the returned RoamNode is immutable (frozen)."""
        node = pull_block_to_roam_node(load_pull_block())
        with pytest.raises(Exception):
            node.uid = "changed"  # type: ignore[misc]
