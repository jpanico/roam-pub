"""Roam Research normalized graph vertex model.

Public symbols:

- :data:`NormalChildren` — ordered list of child block UIDs after normalization.
- :data:`NormalRefs` — list of referenced page/block UIDs after normalization.
- :class:`VertexType` — string enum classifying each vertex in the output graph.
- :class:`Vertex` — normalized, portable representation of a single graph vertex.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from roam_pub.roam_types import HeadingLevel, MediaType, Uid, Url

type NormalChildren = list[Uid]
"""Ordered list of child block UIDs after normalization.

Raw :class:`~roam_pub.roam_types.IdObject` stubs are resolved to stable ``:block/uid``
strings and sorted by ``:block/order`` during the normalization pass.
"""

type NormalRefs = list[Uid]
"""List of referenced page/block UIDs after normalization.

Raw :class:`~roam_pub.roam_types.IdObject` stubs are resolved to stable ``:block/uid``
strings during the normalization pass.
"""


class VertexType(StrEnum):
    """Type identifiers for the individual elements (vertices) in the normalized output graph.

    Every vertex in the output graph has exactly one VertexType.  The values
    are string-valued so they serialize cleanly to/from JSON without extra
    conversion.

    Values:
        ROAM_PAGE: 1-1 with a Roam ``Page`` type node (:node/title present,
            no :block/string).
        ROAM_TEXT_CONTENT: 1-1 with a Roam ``Block`` type node that has no
            ``heading`` property — i.e. normal body text.
        ROAM_HEADING: 1-1 with a Roam ``Block`` type node that has a
            ``heading`` property (value 1, 2, or 3).
        ROAM_IMAGE: A block that references a file uploaded to and managed by Roam
            (Cloud Firestore-hosted); these blocks have a Cloud Firestore URL
            embedded in their ``:block/string``.
    """

    ROAM_PAGE = "roam/page"
    ROAM_TEXT_CONTENT = "roam/text-content"
    ROAM_HEADING = "roam/heading"
    ROAM_IMAGE = "roam/image"


class Vertex(BaseModel):
    """Normalized representation of a Roam graph element.

    After normalization, all internal Datomic ids are eliminated, raw IdObject
    stubs are resolved to stable UIDs, and page-title references in block text
    are replaced with UIDs. The result is a clean, portable graph vertex.

    Attributes:
        uid: Nine-character stable identifier. Required.
        vertex_type: Classification of this vertex. Required.
            Serialized as ``'vertex-type'``.
        media_type: IANA media type. Present only on ROAM_IMAGE vertices.
            Serialized as ``'media-type'``.
        text: Block text content (for ROAM_TEXT_CONTENT / ROAM_HEADING)
            or page title (for ROAM_PAGE). Replaces both ``string`` and ``title``
            from the raw RoamNode.
        heading: HeadingLevel. Present only on ROAM_HEADING vertices.
        children: Ordered list of child UIDs. Replaces raw IdObject stubs.
        refs: List of referenced UIDs. Replaces raw IdObject stubs.
        source: Cloud Firestore storage URL for the file. Present only on ROAM_IMAGE vertices.
        file_name: Original filename. Present only on ROAM_IMAGE vertices.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    uid: Uid = Field(..., description="Nine-character stable block/page identifier")
    vertex_type: VertexType = Field(
        ..., serialization_alias="vertex-type", description="VertexType classification (serialized as 'vertex-type')"
    )
    media_type: MediaType | None = Field(
        default=None,
        serialization_alias="media-type",
        description="IANA media type; present only on ROAM_IMAGE vertices (serialized as 'media-type')",
    )
    text: str | None = Field(
        default=None,
        description="Normalized text: block string for Blocks, page title for Pages",
    )
    heading: HeadingLevel | None = Field(
        default=None, description="HeadingLevel; present only on ROAM_HEADING vertices"
    )
    children: NormalChildren | None = Field(
        default=None, description="Ordered child UIDs resolved from raw IdObject stubs"
    )
    refs: NormalRefs | None = Field(default=None, description="Referenced UIDs resolved from raw IdObject stubs")
    source: Url | None = Field(
        default=None, description="Cloud Firestore storage URL; present only on ROAM_IMAGE vertices"
    )
    file_name: str | None = Field(default=None, description="Original filename; present only on ROAM_IMAGE vertices")
