"""Tests for the roam_page module."""

import logging
from unittest.mock import MagicMock, patch
from pydantic import ValidationError
import pytest
import json
from typing import Any

from roam_pub.roam_asset import ApiEndpointURL
from roam_pub.roam_page import FetchRoamPage, RoamPage

logger = logging.getLogger(__name__)


class TestRoamPage:
    """Tests for the RoamPage Pydantic model."""

    def test_valid_initialization(self) -> None:
        """Test creating RoamPage with valid parameters."""
        pull_block: dict[str, Any] = {
            ":node/title": "My Page",
            ":block/uid": "abc123xyz",
            ":block/children": [],
        }
        page: RoamPage = RoamPage(title="My Page", uid="abc123xyz", pull_block=pull_block)

        assert page.title == "My Page"
        assert page.uid == "abc123xyz"
        assert page.pull_block == pull_block

    def test_empty_title_raises_validation_error(self) -> None:
        """Test that empty title raises a validation error."""
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            RoamPage(title="", uid="abc123xyz", pull_block={":node/title": ""})

    def test_empty_uid_raises_validation_error(self) -> None:
        """Test that empty uid raises a validation error."""
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            RoamPage(title="My Page", uid="", pull_block={":node/title": "My Page"})

    def test_missing_required_fields_raises_validation_error(self) -> None:
        """Test that missing required fields raise validation errors."""
        with pytest.raises(Exception):
            RoamPage(uid="abc123xyz", pull_block={})  # type: ignore[call-arg]

        with pytest.raises(Exception):
            RoamPage(title="My Page", pull_block={})  # type: ignore[call-arg]

        with pytest.raises(Exception):
            RoamPage(title="My Page", uid="abc123xyz")  # type: ignore[call-arg]

    def test_immutability(self) -> None:
        """Test that RoamPage is immutable."""
        page: RoamPage = RoamPage(title="My Page", uid="abc123xyz", pull_block={})
        with pytest.raises(Exception):  # Pydantic raises ValidationError for frozen models
            page.title = "Changed"  # type: ignore[misc]

    def test_pull_block_preserves_nested_structure(self) -> None:
        """Test that deeply nested pull_block dicts are stored correctly."""
        pull_block: dict[str, Any] = {
            ":node/title": "Deep Page",
            ":block/uid": "deep1234x",
            ":block/children": [
                {":block/uid": "child001", ":block/string": "Top level block"},
                {
                    ":block/uid": "child002",
                    ":block/string": "Parent block",
                    ":block/children": [
                        {":block/uid": "child003", ":block/string": "Nested block"},
                    ],
                },
            ],
        }
        page: RoamPage = RoamPage(title="Deep Page", uid="deep1234x", pull_block=pull_block)
        assert page.pull_block[":block/children"][1][":block/children"][0][":block/string"] == "Nested block"


class TestRoamPageFromResponseJson:
    """Tests for FetchRoamPage.roam_page_from_response_json."""

    def _make_response_json(self, title: str, uid: str, extra_attrs: dict | None = None) -> str:
        """Helper to build a realistic Local API data.q response JSON string."""
        pull_block: dict[str, Any] = {
            ":node/title": title,
            ":block/uid": uid,
        }
        if extra_attrs:
            pull_block.update(extra_attrs)
        return json.dumps({"result": [[pull_block]]})

    def test_valid_response_returns_roam_page(self) -> None:
        """Test that a well-formed response is parsed into a RoamPage."""
        response_json = self._make_response_json("My Page", "abc123xyz")
        page: RoamPage | None = FetchRoamPage.roam_page_from_response_json(response_json, "My Page")

        assert page is not None
        assert page.title == "My Page"
        assert page.uid == "abc123xyz"
        assert page.pull_block[":node/title"] == "My Page"

    def test_empty_result_returns_none(self) -> None:
        """Test that an empty result set (page not found) returns None."""
        response_json = json.dumps({"result": []})
        page: RoamPage | None = FetchRoamPage.roam_page_from_response_json(response_json, "Nonexistent Page")

        assert page is None

    def test_pull_block_fully_preserved(self) -> None:
        """Test that the full pull_block dict including extra attributes is preserved."""
        extra_attrs: dict[str, Any] = {
            ":edit/time": 1700000000000,
            ":create/time": 1690000000000,
            ":block/children": [{":db/id": 42}],
        }
        response_json = self._make_response_json("Rich Page", "rich1234x", extra_attrs)
        page: RoamPage | None = FetchRoamPage.roam_page_from_response_json(response_json, "Rich Page")

        assert page is not None
        assert page.pull_block[":edit/time"] == 1700000000000
        assert page.pull_block[":create/time"] == 1690000000000
        assert page.pull_block[":block/children"] == [{":db/id": 42}]

    def test_null_response_json_raises_validation_error(self) -> None:
        """Test that None response_json raises ValidationError."""
        with pytest.raises(ValidationError, match="Input should be a valid string"):
            FetchRoamPage.roam_page_from_response_json(response_json=None, title="My Page")  # type: ignore[arg-type]

    def test_invalid_json_raises_error(self) -> None:
        """Test that invalid JSON raises JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            FetchRoamPage.roam_page_from_response_json("not valid json", "My Page")

    def test_missing_result_key_raises_key_error(self) -> None:
        """Test that a response missing the 'result' key raises KeyError."""
        response_json = json.dumps({"wrong_key": []})
        with pytest.raises(KeyError):
            FetchRoamPage.roam_page_from_response_json(response_json, "My Page")

    def test_missing_block_uid_in_pull_raises_key_error(self) -> None:
        """Test that a pull_block missing ':block/uid' raises KeyError."""
        pull_block = {":node/title": "My Page"}  # No :block/uid
        response_json = json.dumps({"result": [[pull_block]]})
        with pytest.raises(KeyError):
            FetchRoamPage.roam_page_from_response_json(response_json, "My Page")

    def test_title_parameter_populates_roam_page_title(self) -> None:
        """Test that the title parameter (not :node/title from pull) populates RoamPage.title."""
        # The title arg passed in is the authoritative source for RoamPage.title
        response_json = self._make_response_json("Actual Title", "uid000001")
        page: RoamPage | None = FetchRoamPage.roam_page_from_response_json(response_json, "Actual Title")

        assert page is not None
        assert page.title == "Actual Title"


class TestFetchRoamPageFetch:
    """Tests for FetchRoamPage.fetch static method."""

    def test_null_api_endpoint_raises_validation_error(self) -> None:
        """Test that None api_endpoint raises ValidationError."""
        with pytest.raises(ValidationError):
            FetchRoamPage.fetch(api_endpoint=None, api_bearer_token="token", page_title="My Page")  # type: ignore[arg-type]

    def test_null_api_bearer_token_raises_validation_error(self) -> None:
        """Test that None api_bearer_token raises ValidationError."""
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="test-graph")
        with pytest.raises(ValidationError, match="Input should be a valid string"):
            FetchRoamPage.fetch(api_endpoint=endpoint, api_bearer_token=None, page_title="My Page")  # type: ignore[arg-type]

    def test_null_page_title_raises_validation_error(self) -> None:
        """Test that None page_title raises ValidationError."""
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="test-graph")
        with pytest.raises(ValidationError, match="Input should be a valid string"):
            FetchRoamPage.fetch(api_endpoint=endpoint, api_bearer_token="token", page_title=None)  # type: ignore[arg-type]

    def test_http_error_response_raises_http_error(self) -> None:
        """Test that a non-200 HTTP response raises requests.exceptions.HTTPError."""
        import requests

        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="test-graph")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("roam_pub.roam_page.requests.post", return_value=mock_response):
            with pytest.raises(requests.exceptions.HTTPError):
                FetchRoamPage.fetch(api_endpoint=endpoint, api_bearer_token="test-token", page_title="My Page")

    def test_successful_fetch_returns_roam_page(self) -> None:
        """Test that a successful HTTP 200 response returns a RoamPage."""
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="test-graph")
        pull_block: dict[str, Any] = {
            ":node/title": "My Page",
            ":block/uid": "abc123xyz",
            ":edit/time": 1700000000000,
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"result": [[pull_block]]})

        with patch("roam_pub.roam_page.requests.post", return_value=mock_response):
            page: RoamPage | None = FetchRoamPage.fetch(
                api_endpoint=endpoint, api_bearer_token="test-token", page_title="My Page"
            )

        assert page is not None
        assert page.title == "My Page"
        assert page.uid == "abc123xyz"
        assert page.pull_block[":edit/time"] == 1700000000000

    def test_page_not_found_returns_none(self) -> None:
        """Test that an empty result (page not found) returns None."""
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="test-graph")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"result": []})

        with patch("roam_pub.roam_page.requests.post", return_value=mock_response):
            page: RoamPage | None = FetchRoamPage.fetch(
                api_endpoint=endpoint, api_bearer_token="test-token", page_title="Nonexistent"
            )

        assert page is None

    def test_correct_payload_sent_to_api(self) -> None:
        """Test that the correct action and args are sent in the request payload."""
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="test-graph")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"result": []})

        with patch("roam_pub.roam_page.requests.post", return_value=mock_response) as mock_post:
            FetchRoamPage.fetch(api_endpoint=endpoint, api_bearer_token="test-token", page_title="My Page")

        call_kwargs = mock_post.call_args
        payload: dict = call_kwargs.kwargs["json"]
        assert payload["action"] == "data.q"
        assert "My Page" in payload["args"]
        assert any(":node/title" in arg for arg in payload["args"] if isinstance(arg, str))

    def test_bearer_token_in_request_headers(self) -> None:
        """Test that the bearer token is correctly placed in the Authorization header."""
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="test-graph")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"result": []})

        with patch("roam_pub.roam_page.requests.post", return_value=mock_response) as mock_post:
            FetchRoamPage.fetch(api_endpoint=endpoint, api_bearer_token="my-secret-token", page_title="My Page")

        call_kwargs = mock_post.call_args
        headers: dict = call_kwargs.kwargs["headers"]
        assert headers["Authorization"] == "Bearer my-secret-token"

    @pytest.mark.skip(reason="Requires Roam Desktop app running and user logged in")
    def test_live(self) -> None:
        """Live integration test requiring the Roam Desktop app to be running.

        Because this goes through the Local API, the Roam Research native App must be
        running at the time this method is called, and the user must be logged into the
        graph having ``graph_name``.
        """
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="SCFH")
        api_bearer_token = "roam-graph-local-token-OR3s0AcJn5rwxPJ6MYaqnIyjNi7ai"
        page_title = "[[Illustration]] Brief"

        page: RoamPage | None = FetchRoamPage.fetch(
            api_endpoint=endpoint, api_bearer_token=api_bearer_token, page_title=page_title
        )
        logger.info(f"page: {page}")

        assert page is not None
        assert page.title == page_title
        assert len(page.uid) > 0
        assert isinstance(page.pull_block, dict)
        assert page.pull_block.get(":node/title") == page_title
        assert page.pull_block.get(":block/uid") == page.uid
