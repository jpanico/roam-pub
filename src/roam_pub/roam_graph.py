"""Roam Research normalized graph vertex model.

A :class:`Vertex` is the normalized (transcribed) form of a single
:class:`~roam_pub.roam_node.RoamNode`.  A :class:`VertexTree` is the normalized
form of a :class:`~roam_pub.roam_node.NodeTree`.

Normalization (transcription) means:

- Datomic-internal numeric entity ids (:attr:`~roam_pub.roam_node.RoamNode.id`) are
  eliminated.
- Raw :class:`~roam_pub.roam_types.IdObject` stubs in ``children`` and ``refs`` are
  resolved to stable ``:block/uid`` strings.
- The raw ``string`` / ``title`` field distinction is collapsed into a single ``text``
  field.
- Each node is classified into a :class:`VertexType`.
- The result is self-contained and portable — no Datomic dependencies remain.

Normalization is performed by :func:`~roam_pub.roam_transcribe.transcribe` (for a full
:class:`~roam_pub.roam_node.NodeTree`) or
:func:`~roam_pub.roam_transcribe.transcribe_node` (for a single
:class:`~roam_pub.roam_node.RoamNode`).

Public symbols:

- :data:`VertexChildren` — normalized form of
  :attr:`~roam_pub.roam_node.RoamNode.children`: ordered child UIDs.
- :data:`VertexRefs` — normalized form of :attr:`~roam_pub.roam_node.RoamNode.refs`:
  referenced UIDs.
- :class:`VertexType` — string enum classifying each :class:`Vertex` by the shape of
  its source :class:`~roam_pub.roam_node.RoamNode`.
- :class:`Vertex` — normalized (transcribed) form of a single
  :class:`~roam_pub.roam_node.RoamNode`.
- :class:`VertexTree` — normalized (transcribed) form of a
  :class:`~roam_pub.roam_node.NodeTree`; a portable tree of :class:`Vertex` instances.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from roam_pub.roam_types import HeadingLevel, MediaType, Uid, Url

type VertexChildren = list[Uid]
"""Normalized form of :attr:`~roam_pub.roam_node.RoamNode.children`.

Raw :class:`~roam_pub.roam_types.IdObject` stubs are resolved to stable ``:block/uid``
strings and sorted by ``:block/order`` during transcription.
"""

type VertexRefs = list[Uid]
"""Normalized form of :attr:`~roam_pub.roam_node.RoamNode.refs`.

Raw :class:`~roam_pub.roam_types.IdObject` stubs are resolved to stable ``:block/uid``
strings during transcription.
"""


class VertexType(StrEnum):
    """Classification assigned to each :class:`Vertex` during transcription.

    Every :class:`~roam_pub.roam_node.RoamNode` is classified into exactly one
    ``VertexType`` based on the shape of its raw fields.  The values are
    string-valued so they serialize cleanly to/from JSON without extra conversion.

    Values:
        ROAM_PAGE: Normalized form of a Roam *Page* node — ``:node/title`` is
            present; ``:block/string`` is absent.
        ROAM_TEXT_CONTENT: Normalized form of a Roam *Block* node that has no
            ``heading`` property — i.e. normal body text.
        ROAM_HEADING: Normalized form of a Roam *Block* node that carries a
            ``heading`` property (value 1, 2, or 3).
        ROAM_IMAGE: Normalized form of a Roam *Block* node whose
            ``:block/string`` embeds a Cloud Firestore URL pointing to a
            Roam-managed image upload.
    """

    ROAM_PAGE = "roam/page"
    ROAM_TEXT_CONTENT = "roam/text-content"
    ROAM_HEADING = "roam/heading"
    ROAM_IMAGE = "roam/image"


class Vertex(BaseModel):
    """Normalized (transcribed) form of a single :class:`~roam_pub.roam_node.RoamNode`.

    Transcription eliminates the Datomic-internal numeric
    :attr:`~roam_pub.roam_node.RoamNode.id`, resolves raw
    :class:`~roam_pub.roam_types.IdObject` stubs in ``children`` and ``refs`` to
    stable ``:block/uid`` strings, and collapses the ``string`` / ``title`` field
    distinction into a single :attr:`text` field.  The result is a clean,
    self-contained, portable graph vertex with no Datomic dependencies.

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
    children: VertexChildren | None = Field(
        default=None, description="Ordered child UIDs resolved from raw IdObject stubs"
    )
    refs: VertexRefs | None = Field(default=None, description="Referenced UIDs resolved from raw IdObject stubs")
    source: Url | None = Field(
        default=None, description="Cloud Firestore storage URL; present only on ROAM_IMAGE vertices"
    )
    file_name: str | None = Field(default=None, description="Original filename; present only on ROAM_IMAGE vertices")


class VertexTree(BaseModel):
    """Normalized (transcribed) form of a :class:`~roam_pub.roam_node.NodeTree`.

    Produced by :func:`~roam_pub.roam_transcribe.transcribe`, which applies
    :func:`~roam_pub.roam_transcribe.transcribe_node` to every node in the source
    :class:`~roam_pub.roam_node.NodeTree` and collects the results here in the
    same insertion order.  The resulting collection is guaranteed to have exactly
    one :class:`Vertex` per source :class:`~roam_pub.roam_node.RoamNode` and
    inherits the acyclic-tree structure of its origin.

    Attributes:
        vertices: Transcribed vertices, one per source
            :class:`~roam_pub.roam_node.RoamNode`, in insertion order.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    vertices: list[Vertex] = Field(..., description="Transcribed vertices, one per source RoamNode.")
