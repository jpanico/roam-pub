"""Roam Research 'Node' fetching via the Local API.

Public symbols:

- :class:`FetchRoamNodes` — stateless utility class that fetches all Roam nodes
  by various criteria via the Local API's ``data.q`` action, including
  :meth:`~FetchRoamNodes.fetch_roam_nodes` which auto-detects whether *anchor*
  is a page title or a node UID.
"""

import logging
import textwrap
from typing import Final, final

from pydantic import BaseModel, ConfigDict, validate_call

from roam_pub.roam_local_api import (
    ApiEndpoint,
    Request as LocalApiRequest,
    Response as LocalApiResponse,
    invoke_action,
)
from roam_pub.roam_node import RoamNode
from roam_pub.roam_node_fetch_result import QueryAnchorKind, NodeFetchResult, NodeFetchAnchor
from roam_pub.roam_primitives import Uid

logger = logging.getLogger(__name__)


@final
class FetchRoamNodes:
    """Stateless utility class for fetching Roam nodes by various criteria from the Roam Research Local API.

    Executes a Datalog query via the Local API's ``data.q`` action, which proxies
    ``roamAlphaAPI.data.q`` through the Roam Desktop app's local HTTP server.
    """

    def __init__(self) -> None:
        """Prevent instantiation of this stateless utility class."""
        raise TypeError("FetchRoamNodes is a stateless utility class and cannot be instantiated")

    class Request:
        """Namespace for the ``data.q`` request.

        All queries in this namespace use ``(pull ?node [*])`` in their ``:find`` clause.
        The ``pull [*]`` wildcard fetches every DataScript attribute present on each matched
        entity, including ``:block/props`` — the block property key-value map populated by
        Roam extensions such as Augmented Headings (e.g. ``ah-level: h4``).  Block
        properties only appear in the result when they have actually been set on a given
        block; absent block properties are silently omitted, and
        :attr:`~roam_pub.roam_node.RoamNode.props` will be ``None`` for those nodes.

        **Anchor node**: each query opens with a single data pattern clause that binds a
        variable named ``?anchor`` to the node whose attribute matches the caller-supplied
        input variable (``?title`` for page-title queries, ``?uid`` for node-UID queries).
        All subsequent traversal — descendants via ``(descendant ?anchor ?node)`` and page
        references via ``(page-ref ?anchor ?node)`` — radiates outward from ``?anchor``.
        The ``or-join`` join-variable list always includes ``?anchor`` to ensure Datomic
        treats it as the outer binding rather than a fresh free variable.
        """

        _DESCENDANT_CLAUSES: Final[str] = textwrap.indent(
            textwrap.dedent("""\
                [(descendant ?parent ?child)
                    [?parent :block/children ?child]]
                [(descendant ?parent ?child)
                    [?parent :block/children ?mid]
                    (descendant ?mid ?child)]"""),
            "    ",
        )
        _PAGE_REF_CLAUSES: Final[str] = textwrap.indent(
            textwrap.dedent("""\
                [(page-ref ?root ?node)
                    [?root :block/refs ?node]]
                [(page-ref ?root ?node)
                    (descendant ?root ?member)
                    [?member :block/refs ?node]]"""),
            "    ",
        )
        DESCENDANT_RULE: Final[str] = f"[\n{_DESCENDANT_CLAUSES}\n]"
        """Datalog rules vector defining a recursive transitive closure over ``:block/children``.

        Query constants that reference ``(descendant ?parent ?child)`` pass this vector as
        the ``%`` rules binding to resolve the rule at query time.
        """

        PAGE_REF_RULE: Final[str] = f"[\n{_PAGE_REF_CLAUSES}\n]"
        """Datalog rules vector defining the ``page-ref`` rule for ``:block/refs`` traversal.

        ``(page-ref ?root ?node)`` is satisfied when ``?node`` is referenced directly by
        ``?root`` via ``:block/refs`` (clause 1), or when ``?node`` is referenced via
        ``:block/refs`` by any descendant of ``?root`` (clause 2).

        **Dependency**: the second clause calls ``(descendant ?root ?member)``, so
        ``PAGE_REF_RULE`` cannot be used as a standalone rules vector.  Always combine it
        with :attr:`DESCENDANT_RULE` by passing :attr:`DESCENDANT_AND_PAGE_REF_RULES` as the
        ``%`` binding instead.
        """

        DESCENDANT_AND_PAGE_REF_RULES: Final[str] = f"[\n{_DESCENDANT_CLAUSES}\n{_PAGE_REF_CLAUSES}\n]"
        """Combined Datalog rules vector containing both :attr:`DESCENDANT_RULE` and :attr:`PAGE_REF_RULE` clauses.

        Pass this as the ``%`` rules binding for any query that uses both ``(descendant ...)``
        and ``(page-ref ...)``.  Because ``PAGE_REF_RULE`` depends on ``descendant``, the two
        rule sets must be shipped together in a single vector.
        """

        _BY_PAGE_TITLE_QUERY_BASE: Final[str] = textwrap.dedent("""\
            [:find (pull ?node [*])
             :in $ ?title %
             :where
             [?anchor :node/title ?title]
             (or-join [?anchor ?node]
               (and [?anchor :node/title ?title]
                    [?node :node/title ?title])
               (and [?anchor :node/title ?title]
                    (descendant ?anchor ?node))""")
        _PAGE_REF_OR_JOIN_BRANCH: Final[str] = textwrap.indent(
            textwrap.dedent("""\
                (and [?anchor :node/title ?title]
                     (page-ref ?anchor ?node))"""),
            "   ",
        )
        BY_PAGE_TITLE_QUERY: Final[str] = f"{_BY_PAGE_TITLE_QUERY_BASE})]"
        """Datalog query fetching a page and all its descendant blocks by page title.

        Input bindings: ``?title`` (page title string) and ``%`` (rules vector —
        :attr:`DESCENDANT_RULE`).

        The ``or-join`` has two branches:

        1. The anchor node itself (``?node = ?anchor``).
        2. Every block reachable from ``?anchor`` through ``:block/children`` at any depth
           (via the ``descendant`` rule).

        ``or-join`` scoping: ``?anchor`` must appear in the join-variable list
        ``[?anchor ?node]`` *and* be re-bound inside each branch.  Variables from the outer
        ``:where`` clause absent from the join-variable list are treated as fresh free
        variables inside the ``or-join`` — not as the outer binding.  Omitting ``?anchor``
        would cause ``(descendant ?anchor ?node)`` to match every descendant pair in the
        entire graph, returning the full database instead of the target subtree.

        To also include nodes referenced via ``:block/refs``, use
        :attr:`BY_PAGE_TITLE_WITH_REFS_QUERY` instead.
        """

        BY_PAGE_TITLE_WITH_REFS_QUERY: Final[str] = f"{_BY_PAGE_TITLE_QUERY_BASE}\n{_PAGE_REF_OR_JOIN_BRANCH})]"
        """Datalog query fetching a page, all its descendants, and all ``:block/refs`` targets.

        Input bindings: ``?title`` (page title string) and ``%`` (rules vector —
        :attr:`DESCENDANT_AND_PAGE_REF_RULES`).  Must be paired with
        :attr:`DESCENDANT_AND_PAGE_REF_RULES` (not :attr:`DESCENDANT_RULE` alone) because the
        ``page-ref`` rule calls ``(descendant ...)`` internally.

        The ``or-join`` has three branches:

        1. The anchor node itself (``?node = ?anchor``).
        2. Every block reachable from ``?anchor`` through ``:block/children`` at any depth
           (via the ``descendant`` rule).
        3. Every node referenced via ``:block/refs`` from ``?anchor`` directly or from any of
           its descendants (via the ``page-ref`` rule).
        """

        BY_NODE_UID_QUERY: Final[str] = textwrap.dedent("""\
            [:find (pull ?node [*])
             :in $ ?uid %
             :where
             [?anchor :block/uid ?uid]
             (or-join [?anchor ?node]
               (and [?anchor :block/uid ?uid]
                    [?node :block/uid ?uid])
               (and [?anchor :block/uid ?uid]
                    (descendant ?anchor ?node)))]""")
        """Datalog query fetching a node and all its descendant blocks by ``:block/uid``.

        Input bindings: ``?uid`` (nine-character ``:block/uid`` string) and ``%`` (rules
        vector — :attr:`DESCENDANT_RULE`).

        The ``or-join`` has two branches:

        1. The anchor node itself (``?node = ?anchor``).
        2. Every block reachable from ``?anchor`` through ``:block/children`` at any depth
           (via the ``descendant`` rule).

        ``or-join`` scoping: ``?anchor`` must appear in the join-variable list
        ``[?anchor ?node]`` *and* be re-bound inside each branch.  Variables from the outer
        ``:where`` clause absent from the join-variable list are treated as fresh free
        variables inside the ``or-join`` — not as the outer binding.  Omitting ``?anchor``
        would cause ``(descendant ?anchor ?node)`` to match every descendant pair in the
        entire graph, returning the full database instead of the target subtree.
        """

        @staticmethod
        def payload_by_page_title(page_title: str, include_refs: bool = False) -> LocalApiRequest.Payload:
            """Build the ``data.q`` request payload for the given page title.

            Args:
                page_title: The exact title of the Roam page to fetch.
                include_refs: When ``True``, uses :attr:`BY_PAGE_TITLE_WITH_REFS_QUERY`
                    paired with :attr:`DESCENDANT_AND_PAGE_REF_RULES` to also pull every node
                    referenced via ``:block/refs`` from the page or any of its descendants.
                    When ``False`` (default), uses :attr:`BY_PAGE_TITLE_QUERY` paired with
                    :attr:`DESCENDANT_RULE` and returns only the page node and its descendants.

            Returns:
                A :class:`~roam_pub.roam_local_api.Request.Payload` with action ``"data.q"``
                and args set according to *include_refs*.
            """
            if include_refs:
                return LocalApiRequest.Payload(
                    action="data.q",
                    args=[
                        FetchRoamNodes.Request.BY_PAGE_TITLE_WITH_REFS_QUERY,
                        page_title,
                        FetchRoamNodes.Request.DESCENDANT_AND_PAGE_REF_RULES,
                    ],
                )
            return LocalApiRequest.Payload(
                action="data.q",
                args=[FetchRoamNodes.Request.BY_PAGE_TITLE_QUERY, page_title, FetchRoamNodes.Request.DESCENDANT_RULE],
            )

        @staticmethod
        def payload_by_node_uid(node_uid: Uid) -> LocalApiRequest.Payload:
            """Build the ``data.q`` request payload for the given node UID.

            Args:
                node_uid: The nine-character ``:block/uid`` of the node to fetch.

            Returns:
                A :class:`~roam_pub.roam_local_api.Request.Payload` with action
                ``"data.q"`` and args ``[BY_NODE_UID_QUERY, node_uid, DESCENDANT_RULE]``.
            """
            return LocalApiRequest.Payload(
                action="data.q",
                args=[FetchRoamNodes.Request.BY_NODE_UID_QUERY, node_uid, FetchRoamNodes.Request.DESCENDANT_RULE],
            )

    class Response:
        """Namespace for ``data.q`` page response types."""

        class Payload(BaseModel):
            """Parsed ``data.q`` response payload (raw wire format)."""

            model_config = ConfigDict(frozen=True)

            success: bool
            result: list[list[RoamNode]]

    @staticmethod
    def _fetch(
        request_payload: LocalApiRequest.Payload, api_endpoint: ApiEndpoint, lookup_description: str
    ) -> NodeFetchResult:
        """Invoke the Local API, validate the response, and extract the node list.

        Shared implementation used by all public ``fetch_*`` methods.  Callers are
        responsible for building *request_payload* and logging their entry-point
        parameters before calling this method.

        Args:
            request_payload: A fully-constructed ``data.q`` request payload.
            api_endpoint: The API endpoint (URL + bearer token) for the target Roam graph.
            lookup_description: Short human-readable description of the lookup key, used
                in the "no nodes found" log message (e.g. ``"page_title='My Page'"``).

        Returns:
            A list of :class:`RoamNode` instances extracted from the Datalog result
            rows, or an empty list if the query matched nothing.

        Raises:
            requests.exceptions.ConnectionError: If unable to connect to the Local API.
            requests.exceptions.HTTPError: If the Local API returns a non-200 status.
        """
        local_api_response_payload: LocalApiResponse.Payload = invoke_action(request_payload, api_endpoint)
        logger.debug("local_api_response_payload: %s", local_api_response_payload)

        response_payload: FetchRoamNodes.Response.Payload = FetchRoamNodes.Response.Payload.model_validate(
            local_api_response_payload.model_dump(mode="json")
        )
        logger.debug("response_payload: %s", response_payload)

        # Datalog :find returns an array-of-arrays; (pull ...) value is at row[0]
        result: list[list[RoamNode]] = response_payload.result
        nodes: list[RoamNode] = [row[0] for row in result]
        if not nodes:
            logger.info("no nodes found for %s", lookup_description)
        return nodes

    @staticmethod
    @validate_call
    def fetch_by_page_title(
        anchor: NodeFetchAnchor, api_endpoint: ApiEndpoint, include_refs: bool = False
    ) -> NodeFetchResult:
        """Fetch all Roam nodes matching the given page title from the Roam Research Local API.

        Because this goes through the Local API, the Roam Research native App must be
        running at the time this method is called, and the user must be logged into the
        graph.

        Args:
            anchor: The resolved fetch anchor whose
                :attr:`~roam_pub.roam_node_fetch_result.NodeFetchAnchor.target` string is
                the exact title of the Roam page to fetch.
            api_endpoint: The API endpoint (URL + bearer token) for the target Roam graph.
            include_refs: When ``True``, also returns every node referenced via
                ``:block/refs`` from the page or any of its descendants.  When ``False``
                (default), returns only the page node and its descendant blocks.

        Returns:
            A list of :class:`RoamNode` instances comprising the page node itself and
            all its descendant blocks; when *include_refs* is ``True``, also includes
            every node referenced via ``:block/refs`` from the page or any descendant.
            Each node's :attr:`~roam_pub.roam_node.RoamNode.props` field is populated
            when the block has block properties set (e.g. an ``ah-level`` value from
            the Augmented Headings extension).  Returns an empty list if no matching
            page exists.

        Raises:
            ValidationError: If any parameter is ``None`` or invalid.
            ValueError: If ``anchor.kind`` is not :attr:`~roam_pub.roam_node_fetch_result.QueryAnchorKind.PAGE_TITLE`.
            requests.exceptions.ConnectionError: If unable to connect to the Local API.
            requests.exceptions.HTTPError: If the Local API returns a non-200 status.
        """
        logger.debug("api_endpoint: %s, anchor: %r, include_refs: %r", api_endpoint, anchor.target, include_refs)
        if anchor.kind is not QueryAnchorKind.PAGE_TITLE:
            raise ValueError(f"expected anchor.kind=QueryAnchorKind.PAGE_TITLE; got {anchor.kind!r}")
        return FetchRoamNodes._fetch(
            FetchRoamNodes.Request.payload_by_page_title(anchor.target, include_refs=include_refs),
            api_endpoint,
            f"page_title={anchor.target!r}",
        )

    @staticmethod
    @validate_call
    def fetch_by_node_uid(anchor: NodeFetchAnchor, api_endpoint: ApiEndpoint) -> NodeFetchResult:
        """Fetch the Roam node with the given UID and all its descendants from the Local API.

        Because this goes through the Local API, the Roam Research native App must be
        running at the time this method is called, and the user must be logged into the
        graph.

        Args:
            anchor: The resolved fetch anchor whose
                :attr:`~roam_pub.roam_node_fetch_result.NodeFetchAnchor.target` string is
                the nine-character ``:block/uid`` of the root node to fetch.
            api_endpoint: The API endpoint (URL + bearer token) for the target Roam graph.

        Returns:
            A list containing the root :class:`RoamNode` plus every block reachable
            through ``:block/children`` at any depth.  Each node's
            :attr:`~roam_pub.roam_node.RoamNode.props` field is populated when the
            block has block properties set (e.g. an ``ah-level`` value from the
            Augmented Headings extension).  Returns an empty list if no node with
            the given UID exists in the graph.

        Raises:
            ValidationError: If any parameter is ``None`` or invalid.
            ValueError: If ``anchor.kind`` is not :attr:`~roam_pub.roam_node_fetch_result.QueryAnchorKind.NODE_UID`.
            requests.exceptions.ConnectionError: If unable to connect to the Local API.
            requests.exceptions.HTTPError: If the Local API returns a non-200 status.
        """
        logger.debug("api_endpoint: %s, anchor: %r", api_endpoint, anchor.target)
        if anchor.kind is not QueryAnchorKind.NODE_UID:
            raise ValueError(f"expected anchor.kind=QueryAnchorKind.NODE_UID; got {anchor.kind!r}")
        return FetchRoamNodes._fetch(
            FetchRoamNodes.Request.payload_by_node_uid(anchor.target),
            api_endpoint,
            f"node_uid={anchor.target!r}",
        )

    @staticmethod
    def fetch_roam_nodes(
        anchor: NodeFetchAnchor, api_endpoint: ApiEndpoint, include_refs: bool = False
    ) -> NodeFetchResult:
        """Fetch Roam nodes by page title or node UID, dispatching on *anchor* kind.

        Routes to :meth:`fetch_by_node_uid` when
        :attr:`~roam_pub.roam_node_fetch_result.NodeFetchAnchor.kind` is
        :attr:`~roam_pub.roam_node_fetch_result.QueryAnchorKind.NODE_UID`, or to
        :meth:`fetch_by_page_title` otherwise.

        Args:
            anchor: The resolved fetch anchor, carrying both the raw string and its kind.
            api_endpoint: The API endpoint (URL + bearer token) for the target Roam graph.
            include_refs: Forwarded to :meth:`fetch_by_page_title`; ignored when
                *anchor* is a node UID.

        Returns:
            A list of :class:`RoamNode` instances.  Returns an empty list if nothing is found.

        Raises:
            requests.exceptions.ConnectionError: If unable to connect to the Local API.
            requests.exceptions.HTTPError: If the Local API returns a non-200 status.
        """
        if anchor.kind is QueryAnchorKind.NODE_UID:
            return FetchRoamNodes.fetch_by_node_uid(anchor=anchor, api_endpoint=api_endpoint)
        return FetchRoamNodes.fetch_by_page_title(anchor=anchor, api_endpoint=api_endpoint, include_refs=include_refs)
