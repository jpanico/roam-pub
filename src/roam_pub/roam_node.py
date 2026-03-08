"""Roam Research raw node data model.

Public symbols:

- :class:`NodeType` — ``StrEnum`` of pull-block entity types: ``Page``, ``Block``.
- :class:`RoamNode` — raw shape of a pull-block as returned by the Roam Local API.
- :func:`node_type` — return the :class:`NodeType` of a :class:`RoamNode`.
- :data:`NodesByUid` — ``dict`` mapping each :attr:`~RoamNode.uid` to its :class:`RoamNode`.
"""

import enum
import logging
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

logger = logging.getLogger(__name__)


class NodeType(enum.StrEnum):
    """Entity type of a Roam pull-block, discriminated by which of ``title`` / ``string`` is set."""

    Page = "Page"
    Block = "Block"


class RoamNode(BaseModel):
    """Raw shape of a "pull-block" as returned by ``roamAlphaAPI.data.q`` / ``pull [*]``.

    This is the *un-normalized* form — property names mirror the raw Datomic
    attribute names, and nested refs are still IdObject stubs rather than resolved UIDs.

    Every pull-block is one of two mutually exclusive entity types, discriminated by
    which of ``title`` / ``string`` is set.  The following invariants are enforced at
    construction time by :meth:`_validate_entity_type`:

    - **Page**: ``title`` set, ``string`` ``None``, ``parents`` ``None``,
      ``children`` set, ``page`` ``None``.
    - **Block**: ``string`` set, ``title`` ``None``, ``parents`` set,
      ``page`` set, ``children`` any.

    All remaining fields (``heading``, ``open``, ``sidebar``, ``refs``, etc.) are
    optional and vary by entity type and feature usage.

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

    @model_validator(mode="after")
    def _validate_entity_type(self) -> RoamNode:
        """Enforce Page/Block entity-type invariants.

        Returns:
            The validated instance.

        Raises:
            ValueError: If the instance violates the Page or Block field invariants,
                or if neither ``title`` nor ``string`` is set.
        """
        if self.title is not None:
            page_violations: Final[list[str]] = []
            if self.string is not None:
                page_violations.append(f"string must be None; got {self.string!r}")
            if self.parents is not None:
                page_violations.append("parents must be None")
            if self.children is None:
                page_violations.append("children must be set")
            if self.page is not None:
                page_violations.append("page must be None")
            if page_violations:
                raise ValueError(f"Page entity (uid={self.uid!r}) constraint violations: {'; '.join(page_violations)}")
        elif self.string is not None:
            block_violations: Final[list[str]] = []
            if self.parents is None:
                block_violations.append("parents must be set")
            if self.page is None:
                block_violations.append("page must be set")
            if block_violations:
                raise ValueError(
                    f"Block entity (uid={self.uid!r}) constraint violations: {'; '.join(block_violations)}"
                )
        else:
            raise ValueError(
                f"RoamNode (uid={self.uid!r}) must be a Page (title set) or a Block (string set); "
                "got title=None, string=None"
            )
        return self


type NodesByUid = dict[Uid, RoamNode]
"""``dict`` mapping each :attr:`~RoamNode.uid` to its :class:`RoamNode`."""


def node_type(node: RoamNode) -> NodeType:
    """Return the :class:`NodeType` of *node*.

    Discriminates on :attr:`~RoamNode.title`: returns :attr:`NodeType.Page` when
    ``title`` is set, and :attr:`NodeType.Block` otherwise.  The
    :meth:`~RoamNode._validate_entity_type` validator guarantees that every
    :class:`RoamNode` instance satisfies exactly one of these cases.

    Args:
        node: The node whose entity type to determine.

    Returns:
        :attr:`NodeType.Page` if *node* has a ``title``; :attr:`NodeType.Block` otherwise.
    """
    return NodeType.Page if node.title is not None else NodeType.Block
