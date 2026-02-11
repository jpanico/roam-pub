import pytest
import json
import base64
from typing import Any, Dict, List, Tuple
from unittest.mock import Mock, MagicMock, patch, mock_open
import requests

from fetch_roam_file import ApiEndpointURL, FetchRoamFile, fetch_roam_file


class TestApiEndpointURL:
    """Tests for the ApiEndpointURL Pydantic model."""

    def test_valid_initialization(self) -> None:
        """Test creating ApiEndpointURL with valid parameters."""
        endpoint: ApiEndpointURL = ApiEndpointURL(
            local_api_port=3333, graph_name="test-graph"
        )
        assert endpoint.local_api_port == 3333
        assert endpoint.graph_name == "test-graph"

    def test_port_coercion_from_string(self) -> None:
        """Test that local_api_port coerces string to int."""
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port="3333", graph_name="test-graph")  # type: ignore[arg-type]
        assert endpoint.local_api_port == 3333
        assert isinstance(endpoint.local_api_port, int)

    def test_str_representation(self) -> None:
        """Test the string representation of the URL."""
        endpoint: ApiEndpointURL = ApiEndpointURL(
            local_api_port=3333, graph_name="test-graph"
        )
        expected: str = "http://127.0.0.1:3333/api/test-graph"
        assert str(endpoint) == expected

    def test_missing_port_raises_validation_error(self) -> None:
        """Test that missing local_api_port raises a validation error."""
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            ApiEndpointURL(graph_name="test-graph")  # type: ignore[call-arg]

    def test_missing_graph_name_raises_validation_error(self) -> None:
        """Test that missing graph_name raises a validation error."""
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            ApiEndpointURL(local_api_port=3333)  # type: ignore[call-arg]


class TestFetchRoamFileFunction:
    """Tests for the fetch_roam_file function."""

    @pytest.fixture
    def mock_response_success(self) -> Mock:
        """Fixture providing a successful mock response."""
        mock_resp: Mock = Mock()
        mock_resp.status_code = 200

        # Create a realistic response payload
        file_content: bytes = b"test file content"
        encoded_content: str = base64.b64encode(file_content).decode("utf-8")

        response_data: Dict[str, Dict[str, str]] = {
            "result": {"base64": encoded_content, "filename": "test_file.jpeg"}
        }
        mock_resp.text = json.dumps(response_data)
        return mock_resp

    @pytest.fixture
    def mock_response_error(self) -> Mock:
        """Fixture providing an error mock response."""
        mock_resp: Mock = Mock()
        mock_resp.status_code = 404
        mock_resp.text = "File not found"
        return mock_resp

    @patch("fetch_roam_file.requests.post")
    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.print")
    def test_successful_file_fetch(
        self,
        mock_print: MagicMock,
        mock_file: MagicMock,
        mock_post: MagicMock,
        mock_response_success: Mock,
    ) -> None:
        """Test successful file fetching and saving."""
        mock_post.return_value = mock_response_success

        fetch_roam_file(
            local_api_port=3333,
            graph_name="test-graph",
            file_url="https://example.com/file.jpeg",
        )

        # Verify the API was called with correct parameters
        mock_post.assert_called_once()
        call_args: Any = mock_post.call_args

        # Check the endpoint URL
        assert call_args[0][0] == "http://127.0.0.1:3333/api/test-graph"

        # Check the payload
        payload: Dict[str, Any] = call_args.kwargs["json"]
        assert payload["action"] == "file.get"
        assert payload["args"][0]["url"] == "https://example.com/file.jpeg"
        assert payload["args"][0]["format"] == "base64"

        # Check headers
        assert call_args.kwargs["headers"]["Content-Type"] == "application/json"

        # Verify file was opened for writing in binary mode
        mock_file.assert_called_once_with("test_file.jpeg", "wb")

        # Verify file content was written
        handle: MagicMock = mock_file()
        handle.write.assert_called_once_with(b"test file content")

        # Verify success message was printed
        mock_print.assert_any_call("Success! File saved to: test_file.jpeg")

    @patch("fetch_roam_file.requests.post")
    @patch("builtins.print")
    def test_failed_file_fetch(
        self, mock_print: MagicMock, mock_post: MagicMock, mock_response_error: Mock
    ) -> None:
        """Test handling of failed file fetch (404 error)."""
        mock_post.return_value = mock_response_error

        fetch_roam_file(
            local_api_port=3333,
            graph_name="test-graph",
            file_url="https://example.com/missing.jpeg",
        )

        # Verify error message was printed
        mock_print.assert_any_call("Error: Failed to fetch file. Status Code: 404")
        mock_print.assert_any_call("Response: File not found")

    @patch("fetch_roam_file.requests.post")
    @patch("builtins.print")
    def test_connection_error_handling(
        self, mock_print: MagicMock, mock_post: MagicMock
    ) -> None:
        """Test handling of connection errors when API is unreachable."""
        mock_post.side_effect = requests.exceptions.ConnectionError()

        fetch_roam_file(
            local_api_port=3333,
            graph_name="test-graph",
            file_url="https://example.com/file.jpeg",
        )

        # Verify connection error message was printed
        expected_msg: str = (
            "Error: Could not connect to Roam Local API. Is the Roam Desktop App running and Local API enabled?"
        )
        mock_print.assert_any_call(expected_msg)

    @patch("fetch_roam_file.requests.post")
    @patch("builtins.print")
    def test_request_url_construction(
        self, mock_print: MagicMock, mock_post: MagicMock, mock_response_success: Mock
    ) -> None:
        """Test that the API endpoint URL is constructed correctly."""
        mock_post.return_value = mock_response_success

        fetch_roam_file(
            local_api_port=8080,
            graph_name="my-special-graph",
            file_url="https://example.com/file.jpeg",
        )

        # Verify the endpoint URL was constructed correctly
        call_args: Any = mock_post.call_args
        expected_endpoint: str = "http://127.0.0.1:8080/api/my-special-graph"
        assert call_args[0][0] == expected_endpoint

        # Verify the requesting message was printed
        mock_print.assert_any_call(f"Requesting file from: {expected_endpoint}")

    @patch("fetch_roam_file.requests.post")
    @patch("builtins.open", new_callable=mock_open)
    def test_base64_decoding(self, mock_file: MagicMock, mock_post: MagicMock) -> None:
        """Test that base64 content is properly decoded."""
        # Create a mock response with specific base64 content
        test_content: bytes = b"Hello, Roam Research!"
        encoded: str = base64.b64encode(test_content).decode("utf-8")

        mock_resp: Mock = Mock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps(
            {"result": {"base64": encoded, "filename": "test.txt"}}
        )
        mock_post.return_value = mock_resp

        fetch_roam_file(3333, "test", "https://example.com/file")

        # Verify the decoded content was written
        handle: MagicMock = mock_file()
        handle.write.assert_called_once_with(test_content)

    @patch("fetch_roam_file.requests.post")
    @patch("builtins.open", new_callable=mock_open)
    def test_different_file_types(
        self, mock_file: MagicMock, mock_post: MagicMock
    ) -> None:
        """Test fetching different file types (JPEG, PNG, PDF, etc.)."""
        test_cases: List[Tuple[str, bytes]] = [
            ("image.jpeg", b"\xff\xd8\xff\xe0"),  # JPEG magic bytes
            ("document.pdf", b"%PDF-1.4"),  # PDF header
            ("photo.png", b"\x89PNG"),  # PNG signature
        ]

        for filename, content in test_cases:
            encoded: str = base64.b64encode(content).decode("utf-8")

            mock_resp: Mock = Mock()
            mock_resp.status_code = 200
            mock_resp.text = json.dumps(
                {"result": {"base64": encoded, "filename": filename}}
            )
            mock_post.return_value = mock_resp

            fetch_roam_file(3333, "test", f"https://example.com/{filename}")

            # Verify file was opened with correct name
            mock_file.assert_called_with(filename, "wb")
