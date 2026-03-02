"""Roam Research node transcription to normalized graph vertices.

Public symbols:

- :func:`is_image_node` — return ``True`` when a node's string is exactly one
  Markdown image link and nothing else.
- :func:`vertex_type` — classify a :class:`~roam_pub.roam_node.RoamNode` into a
  :class:`~roam_pub.roam_graph.VertexType`.
- :func:`to_page_vertex` — build a :attr:`~roam_pub.roam_graph.VertexType.ROAM_PAGE`
  :class:`~roam_pub.roam_graph.Vertex` from a page node.
- :func:`to_image_vertex` — build a :attr:`~roam_pub.roam_graph.VertexType.ROAM_IMAGE`
  :class:`~roam_pub.roam_graph.Vertex` from a Firestore image block node.
- :func:`to_heading_vertex` — build a :attr:`~roam_pub.roam_graph.VertexType.ROAM_HEADING`
  :class:`~roam_pub.roam_graph.Vertex` from a heading block node.
- :func:`to_text_content_vertex` — build a :attr:`~roam_pub.roam_graph.VertexType.ROAM_TEXT_CONTENT`
  :class:`~roam_pub.roam_graph.Vertex` from a plain text block node.
- :func:`transcribe_node` — transcribe a :class:`~roam_pub.roam_node.RoamNode` into
  a normalized :class:`~roam_pub.roam_graph.Vertex`.
"""

import logging
import mimetypes
import re
from urllib.parse import unquote, urlparse

from pydantic import TypeAdapter, validate_call

from roam_pub.roam_asset import FIRESTORE_IMAGE_RE
from roam_pub.roam_graph import NormalChildren, NormalRefs, Vertex, VertexType
from roam_pub.roam_node import RoamNode
from roam_pub.roam_types import HeadingLevel, Id, Url

logger = logging.getLogger(__name__)

_url_adapter: TypeAdapter[Url] = TypeAdapter(Url)
"""Pydantic :class:`~pydantic.TypeAdapter` for validating and coercing URL strings to.

:data:`~roam_pub.roam_types.Url`.
"""

_IMAGE_LINK_RE: re.Pattern[str] = re.compile(r"!\[(?:[^\]]|\n)*?\]\(https?://[^\)]+\)")
"""Compiled regex matching a single Markdown image link ``![<alt>](<url>)``.

Used by :func:`is_image_node` to verify that a block string consists of exactly
one image link and no surrounding content (after stripping leading/trailing whitespace).
The URL must begin with ``http://`` or ``https://``.
"""


def _resolve_children(node: RoamNode, id_map: dict[Id, RoamNode]) -> NormalChildren | None:
    """Return an ordered list of child UIDs for *node*, or ``None`` if childless.

    Children are sorted by :attr:`~roam_pub.roam_node.RoamNode.order`.  Stubs
    whose id is absent from *id_map* are silently dropped.

    Args:
        node: The node whose children are to be resolved.
        id_map: Mapping from Datomic entity id to :class:`~roam_pub.roam_node.RoamNode`.

    Returns:
        Sorted list of child UIDs, or ``None`` when *node* has no children or
        all child stubs are unresolvable.
    """
    if not node.children:
        return None
    resolved: list[RoamNode] = sorted(
        [id_map[c.id] for c in node.children if c.id in id_map],
        key=lambda n: n.order if n.order is not None else 0,
    )
    uids: NormalChildren = [n.uid for n in resolved]
    return uids if uids else None


def _resolve_refs(node: RoamNode, id_map: dict[Id, RoamNode]) -> NormalRefs | None:
    """Return a list of referenced UIDs for *node*, or ``None`` if there are no refs.

    Stubs whose id is absent from *id_map* are silently dropped.

    Args:
        node: The node whose refs are to be resolved.
        id_map: Mapping from Datomic entity id to :class:`~roam_pub.roam_node.RoamNode`.

    Returns:
        List of referenced UIDs, or ``None`` when *node* has no refs or all ref
        stubs are unresolvable.
    """
    if not node.refs:
        return None
    resolved: NormalRefs = [id_map[r.id].uid for r in node.refs if r.id in id_map]
    return resolved if resolved else None


def _effective_heading_level(node: RoamNode) -> HeadingLevel | None:
    """Return the effective heading level for *node*, or ``None`` if it is not a heading.

    Checks native heading first (``node.heading``, levels 1–3), then falls back
    to the Augmented Headings extension (``node.props['ah-level']``, levels 4–6).

    Args:
        node: The node to inspect.

    Returns:
        An integer heading level in the range 1–6, or ``None``.
    """
    if node.heading is not None:
        return node.heading
    if node.props is not None:
        ah_level = node.props.get("ah-level")
        if isinstance(ah_level, str) and len(ah_level) == 2 and ah_level[0] == "h":
            try:
                level = int(ah_level[1])
                if 1 <= level <= 6:
                    return level
            except ValueError:
                pass
    return None


def _extract_firestore_url(string: str) -> str | None:
    """Return the Cloud Firestore storage URL embedded in *string*, or ``None`` if absent.

    Args:
        string: A raw block string that may contain a Roam markdown image link.

    Returns:
        The URL string captured from the first Firestore image link, or ``None``.
    """
    m = FIRESTORE_IMAGE_RE.search(string)
    return m.group("url") if m else None


def _extract_file_name(firestore_url: str) -> str | None:
    """Return the original filename encoded in a Firestore URL, or ``None`` on failure.

    Firestore URLs encode the object path after ``/o/`` using percent-encoding.
    The filename is the last path segment after URL-decoding.

    Args:
        firestore_url: A ``https://firebasestorage.googleapis.com/...`` URL string.

    Returns:
        The decoded filename (e.g. ``"image.png"``), or ``None`` if extraction fails.
    """
    try:
        path = urlparse(firestore_url).path
        parts = path.split("/o/", maxsplit=1)
        if len(parts) == 2:
            return unquote(parts[1]).split("/")[-1]
    except Exception:
        pass
    return None


def _infer_media_type(file_name: str) -> str | None:
    """Return the IANA media type inferred from *file_name*'s extension, or ``None``.

    Uses :func:`mimetypes.guess_type` from the standard library.

    Args:
        file_name: A filename string including extension (e.g. ``"photo.jpg"``).

    Returns:
        A media type string such as ``"image/jpeg"``, or ``None`` when the type
        cannot be determined.
    """
    guessed, _ = mimetypes.guess_type(file_name)
    return guessed


@validate_call
def is_image_node(node: RoamNode) -> bool:
    """Return ``True`` if *node* contains exactly one Markdown image link and nothing else.

    Checks that ``node.string``, after stripping leading and trailing whitespace,
    consists entirely of a single ``![<alt>](<url>)`` link.  Any surrounding text,
    additional links, or a ``None`` string all return ``False``.

    Args:
        node: The node to inspect.

    Returns:
        ``True`` if ``node.string`` is solely a single Markdown image link.

    Raises:
        ValidationError: If *node* is ``None`` or invalid.
    """
    if node.string is None:
        return False
    return bool(_IMAGE_LINK_RE.fullmatch(node.string.strip()))


@validate_call
def vertex_type(node: RoamNode) -> VertexType:
    r"""Classify *node* into a :class:`~roam_pub.roam_graph.VertexType`.

    Handles both native Roam headings (levels 1–3 via ``node.heading``) and Augmented
    Headings extension levels (4–6 via ``node.props['ah-level']``).

    Classification order:

    1. ``node.title`` is set → :attr:`~roam_pub.roam_graph.VertexType.ROAM_PAGE`
    2. ``node.string`` contains a Firestore URL → :attr:`~roam_pub.roam_graph.VertexType.ROAM_IMAGE`
    3. Effective heading level is non-\ ``None`` → :attr:`~roam_pub.roam_graph.VertexType.ROAM_HEADING`
    4. Otherwise → :attr:`~roam_pub.roam_graph.VertexType.ROAM_TEXT_CONTENT`

    Args:
        node: The raw Roam node to classify.

    Returns:
        The :class:`~roam_pub.roam_graph.VertexType` for *node*.

    Raises:
        ValidationError: If *node* is ``None`` or invalid.
        ValueError: If *node* has neither a ``title`` nor a ``string`` field set.
    """
    logger.debug("node=%r", node)
    if node.title is not None:
        return VertexType.ROAM_PAGE
    string = node.string
    if string is None:
        raise ValueError(f"RoamNode uid={node.uid!r} has neither 'title' nor 'string'")
    if is_image_node(node):
        return VertexType.ROAM_IMAGE
    if _effective_heading_level(node) is not None:
        return VertexType.ROAM_HEADING
    return VertexType.ROAM_TEXT_CONTENT


@validate_call
def to_page_vertex(node: RoamNode, id_map: dict[Id, RoamNode]) -> Vertex:
    """Build a :attr:`~roam_pub.roam_graph.VertexType.ROAM_PAGE` vertex from *node*.

    Args:
        node: A page node with ``node.title`` set.
        id_map: Mapping from Datomic entity id to :class:`~roam_pub.roam_node.RoamNode`,
            used to resolve child and ref stubs to UIDs.

    Returns:
        A :class:`~roam_pub.roam_graph.Vertex` of type
        :attr:`~roam_pub.roam_graph.VertexType.ROAM_PAGE`.

    Raises:
        ValidationError: If *node* or *id_map* is ``None`` or invalid.
        ValueError: If ``node.title`` is ``None``.
    """
    logger.debug("node=%r, id_map keys=%r", node, list(id_map.keys()))
    if node.title is None:
        raise ValueError(f"RoamNode uid={node.uid!r} has no 'title'")
    return Vertex(
        uid=node.uid,
        vertex_type=VertexType.ROAM_PAGE,
        text=node.title,
        children=_resolve_children(node, id_map),
        refs=_resolve_refs(node, id_map),
    )


@validate_call
def to_image_vertex(node: RoamNode, id_map: dict[Id, RoamNode]) -> Vertex:
    """Build a :attr:`~roam_pub.roam_graph.VertexType.ROAM_IMAGE` vertex from *node*.

    Args:
        node: A block node whose ``node.string`` embeds a Firestore image URL.
        id_map: Mapping from Datomic entity id to :class:`~roam_pub.roam_node.RoamNode`,
            used to resolve child and ref stubs to UIDs.

    Returns:
        A :class:`~roam_pub.roam_graph.Vertex` of type
        :attr:`~roam_pub.roam_graph.VertexType.ROAM_IMAGE`.

    Raises:
        ValidationError: If *node* or *id_map* is ``None`` or invalid.
        ValueError: If ``node.string`` is ``None`` or contains no Firestore URL.
    """
    logger.debug("node=%r, id_map keys=%r", node, list(id_map.keys()))
    if node.string is None:
        raise ValueError(f"RoamNode uid={node.uid!r} has no 'string'")
    firestore_url = _extract_firestore_url(node.string)
    if firestore_url is None:
        raise ValueError(f"RoamNode uid={node.uid!r} 'string' contains no Firestore URL")
    file_name = _extract_file_name(firestore_url)
    media_type = _infer_media_type(file_name) if file_name is not None else None
    return Vertex(
        uid=node.uid,
        vertex_type=VertexType.ROAM_IMAGE,
        source=_url_adapter.validate_python(firestore_url),
        file_name=file_name,
        media_type=media_type,
        children=_resolve_children(node, id_map),
        refs=_resolve_refs(node, id_map),
    )


@validate_call
def to_heading_vertex(node: RoamNode, id_map: dict[Id, RoamNode]) -> Vertex:
    """Build a :attr:`~roam_pub.roam_graph.VertexType.ROAM_HEADING` vertex from *node*.

    Args:
        node: A block node with an effective heading level (native ``node.heading``
            or ``node.props['ah-level']``).
        id_map: Mapping from Datomic entity id to :class:`~roam_pub.roam_node.RoamNode`,
            used to resolve child and ref stubs to UIDs.

    Returns:
        A :class:`~roam_pub.roam_graph.Vertex` of type
        :attr:`~roam_pub.roam_graph.VertexType.ROAM_HEADING`.

    Raises:
        ValidationError: If *node* or *id_map* is ``None`` or invalid.
        ValueError: If ``node.string`` is ``None`` or no effective heading level is found.
    """
    logger.debug("node=%r, id_map keys=%r", node, list(id_map.keys()))
    if node.string is None:
        raise ValueError(f"RoamNode uid={node.uid!r} has no 'string'")
    heading = _effective_heading_level(node)
    if heading is None:
        raise ValueError(f"RoamNode uid={node.uid!r} has no effective heading level")
    return Vertex(
        uid=node.uid,
        vertex_type=VertexType.ROAM_HEADING,
        text=node.string,
        heading=heading,
        children=_resolve_children(node, id_map),
        refs=_resolve_refs(node, id_map),
    )


@validate_call
def to_text_content_vertex(node: RoamNode, id_map: dict[Id, RoamNode]) -> Vertex:
    """Build a :attr:`~roam_pub.roam_graph.VertexType.ROAM_TEXT_CONTENT` vertex from *node*.

    Args:
        node: A plain text block node with ``node.string`` set.
        id_map: Mapping from Datomic entity id to :class:`~roam_pub.roam_node.RoamNode`,
            used to resolve child and ref stubs to UIDs.

    Returns:
        A :class:`~roam_pub.roam_graph.Vertex` of type
        :attr:`~roam_pub.roam_graph.VertexType.ROAM_TEXT_CONTENT`.

    Raises:
        ValidationError: If *node* or *id_map* is ``None`` or invalid.
        ValueError: If ``node.string`` is ``None``.
    """
    logger.debug("node=%r, id_map keys=%r", node, list(id_map.keys()))
    if node.string is None:
        raise ValueError(f"RoamNode uid={node.uid!r} has no 'string'")
    return Vertex(
        uid=node.uid,
        vertex_type=VertexType.ROAM_TEXT_CONTENT,
        text=node.string,
        children=_resolve_children(node, id_map),
        refs=_resolve_refs(node, id_map),
    )


@validate_call
def transcribe_node(node: RoamNode, id_map: dict[Id, RoamNode]) -> Vertex:
    r"""Transcribe *node* into a normalized :class:`~roam_pub.roam_graph.Vertex`.

    Determines the :class:`~roam_pub.roam_graph.VertexType` via :func:`vertex_type`,
    resolves raw :class:`~roam_pub.roam_types.IdObject` stubs in children and refs to
    stable UIDs via *id_map*, and handles both native Roam headings (levels 1–3 via
    ``node.heading``) and Augmented Headings extension levels (4–6 via
    ``node.props['ah-level']``).

    Args:
        node: The raw Roam node to transcribe.
        id_map: Mapping from Datomic entity id to :class:`~roam_pub.roam_node.RoamNode`,
            used to resolve child and ref stubs to UIDs.  Stubs whose id is absent
            from *id_map* are silently dropped.

    Returns:
        A :class:`~roam_pub.roam_graph.Vertex` representing the normalized node.

    Raises:
        ValidationError: If *node* or *id_map* is ``None`` or invalid.
        ValueError: If *node* has neither a ``title`` nor a ``string`` field set.
    """
    logger.debug("node=%r, id_map keys=%r", node, list(id_map.keys()))
    match vertex_type(node):
        case VertexType.ROAM_PAGE:
            return to_page_vertex(node, id_map)
        case VertexType.ROAM_IMAGE:
            return to_image_vertex(node, id_map)
        case VertexType.ROAM_HEADING:
            return to_heading_vertex(node, id_map)
        case VertexType.ROAM_TEXT_CONTENT:
            return to_text_content_vertex(node, id_map)
