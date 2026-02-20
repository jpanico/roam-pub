"""Roam Research page fetching via the Local API."""

from string import Template
from typing import Any, Final, TypedDict, cast, final
from pydantic import BaseModel, ConfigDict, Field, validate_call
import requests
import json
import logging

from roam_pub.roam_asset import ApiEndpointURL

logger = logging.getLogger(__name__)


class RoamPage(BaseModel):
    """Immutable representation of a Roam Research page fetched via the Local API.

    Contains the page title, its stable UID, and the full raw PullBlock tree returned
    by the Roam graph query. The pull_block is the nested dict exactly as returned by
    ``(pull ?page [*])`` — callers are responsible for rendering it to Markdown.

    Once created, instances cannot be modified (frozen). All fields are required
    and validated at construction time.
    """

    model_config = ConfigDict(frozen=True)

    title: str = Field(..., min_length=1, description="The page title as queried")
    uid: str = Field(..., min_length=1, description="The page's :block/uid (9-character stable identifier)")
    pull_block: dict[str, Any] = Field(..., description="Full raw PullBlock tree from (pull ?page [*])")


class _DataQPayload(TypedDict):
    """Typed structure for a Roam Local API data.q request payload."""

    action: str
    args: list[str]


class _DataQResponse(TypedDict):
    """Typed structure for a Roam Local API data.q response."""

    result: list[list[dict[str, Any]]]


@final
class FetchRoamPage:
    """Stateless utility class for fetching Roam page content from the Roam Research Local API.

    Executes a Datalog pull query via the Local API's ``data.q`` action, which proxies
    ``roamAlphaAPI.data.q`` through the Roam Desktop app's local HTTP server.

    The query used is::

        [:find (pull ?page [*]) :in $ ?title :where [?page :node/title ?title]]

    This returns all attributes of the page entity whose ``:node/title`` matches the
    given title.

    Class Attributes:
        REQUEST_HEADERS_TEMPLATE: HTTP headers template for all API requests.
        REQUEST_PAYLOAD_TEMPLATE: JSON template for the ``data.q`` request payload.
            Expects ``$page_title`` substitution. The ``args`` array passes the Datalog
            query string first, then the title value as an input binding (``?title``).
    """

    def __init__(self) -> None:
        """Prevent instantiation of this stateless utility class."""
        raise TypeError("FetchRoamPage is a stateless utility class and cannot be instantiated")

    REQUEST_HEADERS_TEMPLATE: Final[Template] = Template("""
    {
        "Content-Type": "application/json",
        "Authorization": "Bearer $roam_local_api_token"
    }
    """)

    REQUEST_PAYLOAD_TEMPLATE: Final[Template] = Template("""
    {
        "action": "data.q",
        "args": [
            "[:find (pull ?page [*]) :in $$ ?title :where [?page :node/title ?title]]",
            "$page_title"
        ]
    }
    """)

    @staticmethod
    @validate_call
    def roam_page_from_response_json(response_json: str, title: str) -> RoamPage | None:
        """Parse a Roam Local API ``data.q`` JSON response into a RoamPage.

        Args:
            response_json: The raw JSON response text from the Local API.
            title: The page title that was queried (carried through to populate RoamPage.title).

        Returns:
            A RoamPage instance if the page was found, or None if the result set is empty
            (i.e. no page with that title exists in the graph).

        Raises:
            json.JSONDecodeError: If response_json is not valid JSON.
            KeyError: If the response is missing expected keys.
        """
        logger.debug(f"response_json: {response_json}")

        response_payload: _DataQResponse = cast(_DataQResponse, json.loads(response_json))
        result: list[list[dict[str, Any]]] = response_payload["result"]

        if not result:
            logger.info(f"No page found with title: {title!r}")
            return None

        # Datalog :find returns an array-of-arrays; (pull ...) value is at result[0][0]
        pull_block: dict[str, Any] = result[0][0]
        uid: str = cast(str, pull_block[":block/uid"])

        logger.info(f"Successfully fetched page: {title!r} (uid={uid})")

        return RoamPage(title=title, uid=uid, pull_block=pull_block)

    @staticmethod
    @validate_call
    def fetch(api_endpoint: ApiEndpointURL, api_bearer_token: str, page_title: str) -> RoamPage | None:
        """Fetch a Roam page by title from the Roam Research Local API.

        Because this goes through the Local API, the Roam Research native App must be
        running at the time this method is called, and the user must be logged into the
        graph having ``graph_name``.

        Args:
            api_endpoint: The API endpoint URL (validated by Pydantic).
            api_bearer_token: The bearer token for authenticating with the Roam Local API.
            page_title: The exact title of the Roam page to fetch.

        Returns:
            A RoamPage containing the page's uid and full PullBlock tree, or None if no
            page with that title exists in the graph.

        Raises:
            ValidationError: If any parameter is None or invalid.
            requests.exceptions.ConnectionError: If unable to connect to the Local API.
            requests.exceptions.HTTPError: If the Local API returns a non-200 status.
        """
        logger.debug(f"api_endpoint: {api_endpoint}, page_title: {page_title!r}")

        request_headers_str: str = FetchRoamPage.REQUEST_HEADERS_TEMPLATE.substitute(
            roam_local_api_token=api_bearer_token
        )
        request_headers: dict[str, str] = cast(dict[str, str], json.loads(request_headers_str))

        request_payload_str: str = FetchRoamPage.REQUEST_PAYLOAD_TEMPLATE.substitute(page_title=page_title)
        request_payload: _DataQPayload = cast(_DataQPayload, json.loads(request_payload_str))
        logger.info(f"request_payload: {request_payload}, headers: {request_headers}, api: {api_endpoint}")

        response: requests.Response = requests.post(
            str(api_endpoint), json=request_payload, headers=request_headers, stream=False
        )

        if response.status_code == 200:
            return FetchRoamPage.roam_page_from_response_json(response.text, page_title)
        else:
            error_msg: str = f"Failed to fetch page. Status Code: {response.status_code}, Response: {response.text}"
            logger.error(error_msg)
            raise requests.exceptions.HTTPError(error_msg)
