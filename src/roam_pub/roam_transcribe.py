"""Transcription of Roam Research graph data to Markdown."""

from typing import Any

from roam_pub.roam_model import RoamNode


def pull_block_to_roam_node(pull_block: dict[str, Any]) -> RoamNode:
    """Convert a raw pull block dict from ``roamAlphaAPI.data.q`` into a ``RoamNode``.

    The Local API returns pull block dicts with short unnamespaced keys
    (e.g. ``"uid"``, ``"id"``, ``"title"``, ``"children"``) that map directly
    to ``RoamNode`` field names. Unknown keys not modelled by ``RoamNode``
    (e.g. ``"prevent-clean"``) are silently ignored.

    Args:
        pull_block: A single pull block dict as found at ``result[0][0]``
            in a ``data.q`` response, or in the ``children`` list of another
            pull block.

    Returns:
        A ``RoamNode`` populated from the pull block data.

    Raises:
        pydantic.ValidationError: If required fields (``uid``, ``id``) are
            absent or any present field value fails type validation.
    """
    return RoamNode.model_validate(pull_block)
