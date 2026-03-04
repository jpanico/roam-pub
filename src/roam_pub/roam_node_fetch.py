"""Roam Research 'Node' fetching via the Local API.

Public symbols:

- :class:`FetchRoamNodes` — stateless utility class that fetches all Roam nodes
  by various criteria via the Local API's ``data.q`` action.
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
        """

        BY_PAGE_TITLE_QUERY: Final[str] = textwrap.dedent("""\
            [:find (pull ?node [*])
             :in $ ?title %
             :where
             [?page :node/title ?title]
             (or-join [?page ?node]
               (and [?page :node/title ?title]
                    [?node :node/title ?title])
               (and [?page :node/title ?title]
                    (descendant ?page ?node)))]""")
        """Datalog query fetching a page and all its descendant blocks by ``:node/title``.

        Input bindings: ``?title`` (page title string) and ``%`` (rules vector —
        :attr:`DESCENDANT_RULE`).  See :attr:`DESCENDANT_RULE` for the traversal structure.
        """

        DESCENDANT_RULE: Final[str] = textwrap.dedent("""\
            [
                [(descendant ?parent ?child)
                    [?parent :block/children ?child]]
                [(descendant ?parent ?child)
                    [?parent :block/children ?mid]
                    (descendant ?mid ?child)]
            ]""")
        """Datalog rules vector defining a recursive transitive closure over ``:block/children``.

        Both query constants use an ``or-join`` with this rule to return the root node itself
        (first branch) plus every block reachable through ``:block/children`` at any depth
        (second branch).

        ``or-join`` scoping: the root variable (``?page`` or ``?root``) must appear in the
        join-variable list *and* be re-bound inside each branch.  Variables from the outer
        ``:where`` clause that are absent from the join-variable list are treated as fresh
        free variables inside the ``or-join`` — not as the outer binding.  Omitting the root
        variable would cause ``(descendant ?root ?node)`` to match every descendant pair in
        the entire graph, returning the full database instead of the target subtree.
        """

        BY_NODE_UID_QUERY: Final[str] = textwrap.dedent("""\
            [:find (pull ?node [*])
             :in $ ?uid %
             :where
             [?root :block/uid ?uid]
             (or-join [?root ?node]
               (and [?root :block/uid ?uid]
                    [?node :block/uid ?uid])
               (and [?root :block/uid ?uid]
                    (descendant ?root ?node)))]""")
        """Datalog query fetching a node and all its descendant blocks by ``:block/uid``.

        Input bindings: ``?uid`` (nine-character ``:block/uid`` string) and ``%`` (rules
        vector — :attr:`DESCENDANT_RULE`).  See :attr:`DESCENDANT_RULE` for the traversal
        structure.
        """

        @staticmethod
        def payload_by_page_title(page_title: str) -> LocalApiRequest.Payload:
            """Build the ``data.q`` request payload for the given page title.

            Args:
                page_title: The exact title of the Roam page to fetch.

            Returns:
                A :class:`~roam_pub.roam_local_api.Request.Payload` with action
                ``"data.q"`` and args ``[BY_PAGE_TITLE_QUERY, page_title]``.
            """
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
    ) -> list[RoamNode]:
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
        logger.debug(f"local_api_response_payload: {local_api_response_payload}")

        response_payload: FetchRoamNodes.Response.Payload = FetchRoamNodes.Response.Payload.model_validate(
            local_api_response_payload.model_dump(mode="json")
        )
        logger.debug(f"response_payload: {response_payload}")

        # Datalog :find returns an array-of-arrays; (pull ...) value is at row[0]
        result: list[list[RoamNode]] = response_payload.result
        nodes: list[RoamNode] = [row[0] for row in result]
        if not nodes:
            logger.info(f"no nodes found for {lookup_description}")
        return nodes

    @staticmethod
    @validate_call
    def fetch_by_page_title(page_title: str, api_endpoint: ApiEndpoint) -> list[RoamNode]:
        """Fetch all Roam nodes matching the given page title from the Roam Research Local API.

        Because this goes through the Local API, the Roam Research native App must be
        running at the time this method is called, and the user must be logged into the
        graph.

        Args:
            page_title: The exact title of the Roam page to fetch.
            api_endpoint: The API endpoint (URL + bearer token) for the target Roam graph.

        Returns:
            A list of :class:`RoamNode` instances whose ``:node/title`` matches
            ``page_title``.  Each node's :attr:`~roam_pub.roam_node.RoamNode.props`
            field is populated when the block has block properties set (e.g. an
            ``ah-level`` value from the Augmented Headings extension).
            Returns an empty list if no matching page exists.

        Raises:
            ValidationError: If any parameter is ``None`` or invalid.
            requests.exceptions.ConnectionError: If unable to connect to the Local API.
            requests.exceptions.HTTPError: If the Local API returns a non-200 status.
        """
        logger.debug(f"api_endpoint: {api_endpoint}, page_title: {page_title!r}")
        return FetchRoamNodes._fetch(
            FetchRoamNodes.Request.payload_by_page_title(page_title),
            api_endpoint,
            f"page_title={page_title!r}",
        )

    @staticmethod
    @validate_call
    def fetch_by_node_uid(node_uid: Uid, api_endpoint: ApiEndpoint) -> list[RoamNode]:
        """Fetch the Roam node with the given UID and all its descendants from the Local API.

        Because this goes through the Local API, the Roam Research native App must be
        running at the time this method is called, and the user must be logged into the
        graph.

        Args:
            node_uid: The nine-character ``:block/uid`` of the root node to fetch.
            api_endpoint: The API endpoint (URL + bearer token) for the target Roam graph.

        Returns:
            A list containing the root :class:`RoamNode` plus every block reachable
            through ``:block/children`` at any depth.  Each node's
            :attr:`~roam_pub.roam_node.RoamNode.props` field is populated when the
            block has block properties set (e.g. an ``ah-level`` value from the
            Augmented Headings extension).  Returns an empty list if no node with
            ``node_uid`` exists in the graph.

        Raises:
            ValidationError: If any parameter is ``None`` or invalid.
            requests.exceptions.ConnectionError: If unable to connect to the Local API.
            requests.exceptions.HTTPError: If the Local API returns a non-200 status.
        """
        logger.debug(f"api_endpoint: {api_endpoint}, node_uid: {node_uid!r}")
        return FetchRoamNodes._fetch(
            FetchRoamNodes.Request.payload_by_node_uid(node_uid),
            api_endpoint,
            f"node_uid={node_uid!r}",
        )
