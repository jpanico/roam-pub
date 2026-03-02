"""Foundational Roam Research type aliases and stub models.

Public symbols are organized into three groups:

- **Primitive type aliases**: :data:`Uid`, :data:`Id`, :data:`Order`, :data:`HeadingLevel`,
  :data:`PageTitle`, :data:`Url`, :data:`MediaType`.
- **Composite type aliases**: :data:`UidPair`, :data:`RawChildren`, :data:`RawRefs`.
- **Stub models**: :class:`IdObject`, :class:`LinkObject`.
"""

import logging
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

logger = logging.getLogger(__name__)

type Uid = Annotated[str, Field(pattern=r"^[A-Za-z0-9-]{9}$")]
"""Nine-character alphanumeric stable block/page identifier (:block/uid)."""

type Id = int
"""Datomic internal numeric entity id (:db/id).

Ephemeral — not stable across exports.
"""

type Order = Annotated[int, Field(ge=0)]
"""Zero-based position of a child block among its siblings (:block/order)."""

type HeadingLevel = Annotated[int, Field(ge=1, le=6)]
"""Markdown heading level 1–6 (:block/heading).

Absent (None) on non-heading blocks.
"""

type PageTitle = Annotated[str, Field(min_length=1)]
"""Page title string (:node/title).

Only present on page entities.
"""

type Url = HttpUrl
"""A validated HTTP/HTTPS URL (e.g. a Cloud Firestore storage URL for a Roam-managed file)."""

type MediaType = Annotated[str, Field(pattern=r"^[\w-]+/[\w-]+$")]
"""IANA media type (MIME type) string, e.g. ``"image/jpeg"``.

Must match the pattern ``<type>/<subtype>`` where both components consist of
word characters and hyphens (e.g. ``"image/jpeg"``, ``"application/pdf"``).

References:
  - https://en.wikipedia.org/wiki/Media_type
  - https://www.iana.org/assignments/media-types/media-types.xhtml
"""

type UidPair = tuple[str, Uid]
"""A two-element tuple ``('uid', <uid-value>)`` used as a Datomic :entity/attrs source or value."""


class IdObject(BaseModel):
    """A thin wrapper carrying only a Datomic entity id.

    This is the stub shape returned by ``pull [*]`` for nested refs
    (e.g. ``:block/children``, ``:block/refs``, ``:block/page``) when
    those entities were not themselves pulled in full.

    Attributes:
        id: The Datomic internal numeric entity id (:db/id).
    """

    model_config = ConfigDict(frozen=True)

    id: Id = Field(..., description="Datomic internal numeric entity id (:db/id)")


class LinkObject(BaseModel):
    """A :entity/attrs link entry, representing a typed attribute assertion.

    Each entry in a ``:entity/attrs`` value is a ``LinkObject`` carrying a
    source UidPair (the attribute identity) and a value UidPair (the asserted
    value).

    Attributes:
        source: ``('uid', <attr-uid>)`` — the attribute being asserted.
        value: ``('uid', <value-uid>)`` — the value of the assertion.
    """

    model_config = ConfigDict(frozen=True)

    source: UidPair = Field(..., description="Attribute identity as a ('uid', uid) pair")
    value: UidPair = Field(..., description="Asserted value as a ('uid', uid) pair")


type RawChildren = list[IdObject]
"""Child block stubs as returned directly by ``pull [*]``.

Each element is an :class:`IdObject` carrying only a ``:db/id``; full block data
is resolved during the normalization pass.
"""

type RawRefs = list[IdObject]
"""Page/block reference stubs as returned directly by ``pull [*]``.

Same shape as :data:`RawChildren` — :class:`IdObject` stubs awaiting normalization.
"""
