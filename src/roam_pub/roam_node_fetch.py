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
        """Namespace for the ``data.q`` request."""

        # or-join scoping: ?page must be in the join-variable list AND re-bound inside each branch.
        # Variables from the outer :where clause that are NOT in the join-variable list are treated
        # as fresh free variables inside the or-join — not as the outer binding. Omitting ?page from
        # [?page ?node] would cause (descendant ?page ?node) to match every descendant pair in the
        # entire graph, returning the full database instead of just this page's subtree.
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
        """Datalog query fetching the page entity and all its descendant blocks by title.

        Returns the page node itself (first ``or-join`` branch) plus every block reachable
        through ``:block/children`` at any depth (second branch, driven by
        :attr:`DESCENDANT_RULE`).  Input bindings: ``?title`` (page title string) and
        ``%`` (rules vector — :attr:`DESCENDANT_RULE`).

        The ``pull [*]`` wildcard fetches every DataScript attribute present on each entity,
        including ``:block/props`` — the block property key-value map populated by Roam
        extensions such as Augmented Headings (e.g. ``ah-level: h4``).  Block properties
        only appear in the result when they have actually been set on a given block; absent
        block properties are silently omitted, and :attr:`~roam_pub.roam_node.RoamNode.props`
        will be ``None`` for those nodes.
        """

        DESCENDANT_RULE: Final[str] = textwrap.dedent("""\
            [
                [(descendant ?parent ?child) 
                    [?parent :block/children ?child]] 
                [(descendant ?parent ?child) 
                    [?parent :block/children ?mid] 
                    (descendant ?mid ?child)]
            ]""")

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

    class Response:
        """Namespace for ``data.q`` page response types."""

        class Payload(BaseModel):
            """Parsed ``data.q`` response payload (raw wire format)."""

            model_config = ConfigDict(frozen=True)

            success: bool
            result: list[list[RoamNode]]

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

        request_payload: LocalApiRequest.Payload = FetchRoamNodes.Request.payload_by_page_title(page_title)
        local_api_response_payload: LocalApiResponse.Payload = invoke_action(request_payload, api_endpoint)
        logger.debug(f"local_api_response_payload: {local_api_response_payload}")

        page_response_payload: FetchRoamNodes.Response.Payload = FetchRoamNodes.Response.Payload.model_validate(
            local_api_response_payload.model_dump(mode="json")
        )
        logger.debug(f"page_response_payload: {page_response_payload}")

        # Datalog :find returns an array-of-arrays; (pull ...) value is at row[0]
        result: list[list[RoamNode]] = page_response_payload.result
        nodes: list[RoamNode] = [row[0] for row in result]
        if not nodes:
            logger.info(f"no nodes found for page_title: {page_title!r}")
        return nodes
