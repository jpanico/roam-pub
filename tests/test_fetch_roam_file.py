import logging
from pydantic import HttpUrl
import pytest
import json
import base64
from datetime import datetime
from typing import List, Tuple

from mdplay.fetch_roam_file import ApiEndpointURL, RoamFile, FetchRoamFile

logger = logging.getLogger(__name__)


class TestApiEndpointURL:
    """Tests for the ApiEndpointURL Pydantic model."""

    def test_valid_initialization(self) -> None:
        """Test creating ApiEndpointURL with valid parameters."""
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="test-graph")
        assert endpoint.local_api_port == 3333
        assert endpoint.graph_name == "test-graph"

    def test_port_coercion_from_string(self) -> None:
        """Test that local_api_port coerces string to int."""
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port="3333", graph_name="test-graph")  # type: ignore[arg-type]
        assert endpoint.local_api_port == 3333
        assert isinstance(endpoint.local_api_port, int)

    def test_str_representation(self) -> None:
        """Test the string representation of the URL."""
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="test-graph")
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

    def test_immutability(self) -> None:
        """Test that ApiEndpointURL is immutable."""
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="test-graph")
        with pytest.raises(Exception):  # Pydantic raises ValidationError for frozen models
            endpoint.local_api_port = 8080  # type: ignore[misc]


class TestRoamFile:
    """Tests for the RoamFile Pydantic model."""

    def test_valid_initialization(self) -> None:
        """Test creating RoamFile with valid parameters."""
        test_datetime: datetime = datetime(2024, 1, 15, 10, 30, 0)
        test_contents: bytes = b"test file content"

        roam_file: RoamFile = RoamFile(
            file_name="test.jpeg",
            last_modified=test_datetime,
            media_type="image/jpeg",
            contents=test_contents,
        )

        assert roam_file.file_name == "test.jpeg"
        assert roam_file.last_modified == test_datetime
        assert roam_file.media_type == "image/jpeg"
        assert roam_file.contents == test_contents

    def test_empty_filename_raises_validation_error(self) -> None:
        """Test that empty file_name raises a validation error."""
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            RoamFile(
                file_name="",  # Empty string
                last_modified=datetime.now(),
                media_type="image/jpeg",
                contents=b"data",
            )

    def test_invalid_media_type_raises_validation_error(self) -> None:
        """Test that invalid media_type format raises a validation error."""
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            RoamFile(
                file_name="test.txt",
                last_modified=datetime.now(),
                media_type="invalid",  # Missing slash
                contents=b"data",
            )

    def test_valid_media_types(self) -> None:
        """Test various valid MIME type formats."""
        valid_media_types: List[str] = [
            "image/jpeg",
            "image/png",
            "application/pdf",
            "text/plain",
            "video/mp4",
        ]

        for media_type in valid_media_types:
            roam_file: RoamFile = RoamFile(
                file_name="test.file",
                last_modified=datetime.now(),
                media_type=media_type,
                contents=b"data",
            )
            assert roam_file.media_type == media_type

    def test_missing_required_fields_raises_validation_error(self) -> None:
        """Test that missing required fields raise validation errors."""
        # Missing file_name
        with pytest.raises(Exception):
            RoamFile(last_modified=datetime.now(), media_type="image/jpeg", contents=b"data")  # type: ignore[call-arg]

        # Missing last_modified
        with pytest.raises(Exception):
            RoamFile(file_name="test.jpeg", media_type="image/jpeg", contents=b"data")  # type: ignore[call-arg]

        # Missing media_type
        with pytest.raises(Exception):
            RoamFile(file_name="test.jpeg", last_modified=datetime.now(), contents=b"data")  # type: ignore[call-arg]

        # Missing contents
        with pytest.raises(Exception):
            RoamFile(file_name="test.jpeg", last_modified=datetime.now(), media_type="image/jpeg")  # type: ignore[call-arg]

    def test_bytes_contents_validation(self) -> None:
        """Test that contents must be bytes."""
        roam_file: RoamFile = RoamFile(
            file_name="test.txt", last_modified=datetime.now(), media_type="text/plain", contents=b"binary data"
        )
        assert isinstance(roam_file.contents, bytes)

    def test_different_file_types(self) -> None:
        """Test RoamFile with different file types and their typical MIME types."""
        test_cases: List[Tuple[str, str, bytes]] = [
            ("image.jpeg", "image/jpeg", b"\xff\xd8\xff\xe0"),  # JPEG magic bytes
            ("document.pdf", "application/pdf", b"%PDF-1.4"),  # PDF header
            ("photo.png", "image/png", b"\x89PNG"),  # PNG signature
            ("data.json", "application/json", b'{"key": "value"}'),
        ]

        for file_name, media_type, contents in test_cases:
            roam_file: RoamFile = RoamFile(
                file_name=file_name, last_modified=datetime.now(), media_type=media_type, contents=contents
            )
            assert roam_file.file_name == file_name
            assert roam_file.media_type == media_type
            assert roam_file.contents == contents

    def test_datetime_coercion_from_string(self) -> None:
        """Test that last_modified coerces string to datetime."""
        # ISO 8601 format string
        roam_file: RoamFile = RoamFile(
            file_name="test.txt",
            last_modified="2024-01-15T10:30:00",  # type: ignore[arg-type]
            media_type="text/plain",
            contents=b"data",
        )
        assert isinstance(roam_file.last_modified, datetime)
        assert roam_file.last_modified.year == 2024
        assert roam_file.last_modified.month == 1
        assert roam_file.last_modified.day == 15
        assert roam_file.last_modified.hour == 10
        assert roam_file.last_modified.minute == 30

    def test_immutability(self) -> None:
        """Test that RoamFile is immutable."""
        roam_file: RoamFile = RoamFile(
            file_name="test.txt", last_modified=datetime.now(), media_type="text/plain", contents=b"data"
        )
        with pytest.raises(Exception):  # Pydantic raises ValidationError for frozen models
            roam_file.file_name = "changed.txt"  # type: ignore[misc]


class TestRoamFileFromResponseText:
    """Tests for the FetchRoamFile.roam_file_from_response_text static method."""

    def test_null_response_text_raises_type_error(self) -> None:
        """Test that None response_text raises TypeError."""
        with pytest.raises(TypeError, match="response_text cannot be None"):
            FetchRoamFile.roam_file_from_response_text(response_text=None)  # type: ignore[arg-type]

    def test_valid_response_text_returns_roam_file(self) -> None:
        """Test that valid response text returns a RoamFile object."""
        # Create a realistic response payload
        file_content: bytes = b"test file content"
        encoded_content: str = base64.b64encode(file_content).decode("utf-8")

        response_json: str = json.dumps(
            {"result": {"base64": encoded_content, "filename": "test_file.jpeg", "mimetype": "image/jpeg"}}
        )

        roam_file: RoamFile = FetchRoamFile.roam_file_from_response_text(response_json)

        assert roam_file.file_name == "test_file.jpeg"
        assert roam_file.contents == file_content
        assert roam_file.media_type == "image/jpeg"
        assert isinstance(roam_file.last_modified, datetime)

    def test_base64_decoding(self) -> None:
        """Test that base64 content is properly decoded."""
        test_content: bytes = b"Hello, Roam Research!"
        encoded: str = base64.b64encode(test_content).decode("utf-8")

        response_json: str = json.dumps(
            {"result": {"base64": encoded, "filename": "test.txt", "mimetype": "text/plain"}}
        )

        roam_file: RoamFile = FetchRoamFile.roam_file_from_response_text(response_json)

        assert roam_file.contents == test_content
        assert roam_file.file_name == "test.txt"
        assert roam_file.media_type == "text/plain"

    def test_different_file_types(self) -> None:
        """Test parsing responses with different file types."""
        test_cases: List[Tuple[str, bytes, str]] = [
            ("image.jpeg", b"\xff\xd8\xff\xe0", "image/jpeg"),  # JPEG magic bytes
            ("document.pdf", b"%PDF-1.4", "application/pdf"),  # PDF header
            ("photo.png", b"\x89PNG", "image/png"),  # PNG signature
        ]

        for filename, content, mediat_type in test_cases:
            encoded: str = base64.b64encode(content).decode("utf-8")
            response_json: str = json.dumps(
                {"result": {"base64": encoded, "filename": filename, "mimetype": mediat_type}}
            )

            roam_file: RoamFile = FetchRoamFile.roam_file_from_response_text(response_json)

            assert roam_file.file_name == filename
            assert roam_file.contents == content
            assert roam_file.media_type == mediat_type

    def test_invalid_json_raises_error(self) -> None:
        """Test that invalid JSON raises an error."""
        with pytest.raises(json.JSONDecodeError):
            FetchRoamFile.roam_file_from_response_text("not valid json")

    def test_missing_result_key_raises_error(self) -> None:
        """Test that missing 'result' key raises KeyError."""
        response_json: str = json.dumps({"wrong_key": {}})

        with pytest.raises(KeyError):
            FetchRoamFile.roam_file_from_response_text(response_json)

    def test_missing_base64_key_raises_error(self) -> None:
        """Test that missing 'base64' key raises KeyError."""
        response_json: str = json.dumps({"result": {"filename": "test.txt"}})

        with pytest.raises(KeyError):
            FetchRoamFile.roam_file_from_response_text(response_json)

    def test_missing_filename_key_raises_error(self) -> None:
        """Test that missing 'filename' key raises KeyError."""
        encoded: str = base64.b64encode(b"data").decode("utf-8")
        response_json: str = json.dumps({"result": {"base64": encoded}})

        with pytest.raises(KeyError):
            FetchRoamFile.roam_file_from_response_text(response_json)


class TestFetchRoamFileFetch:
    """Tests for the FetchRoamFile.fetch static method."""

    def test_null_api_endpoint_raises_type_error(self) -> None:
        """Test that None api_endpoint raises TypeError."""
        with pytest.raises(TypeError, match="api_endpoint cannot be None"):
            FetchRoamFile.fetch(api_endpoint=None, firebase_url="https://example.com/file.jpeg")  # type: ignore[arg-type]

    def test_null_file_url_raises_type_error(self) -> None:
        """Test that None file_url raises TypeError."""
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="test-graph")
        with pytest.raises(TypeError, match="file_url cannot be None"):
            FetchRoamFile.fetch(api_endpoint=endpoint, firebase_url=None)  # type: ignore[arg-type]

    # @pytest.mark.skip(reason="Requires Roam Desktop app running and user logged in")
    def test_live(self) -> None:
        """
        Because this goes through the Local API, the Roam Research native App must be running at the time
        this method is called, and the user must be logged into the graph having `graph_name`
        """
        endpoint: ApiEndpointURL = ApiEndpointURL(local_api_port=3333, graph_name="SCFH")
        url: HttpUrl = HttpUrl(
            "https://firebasestorage.googleapis.com/v0/b/firescript-577a2.appspot.com/o/imgs%2Fapp%2FSCFH%2F-9owRBegJ8.jpeg.enc?alt=media&token=9b673aae-8089-4a91-84df-9dac152a7f94"
        )
        roam_file: RoamFile = FetchRoamFile.fetch(api_endpoint=endpoint, firebase_url=url)
        logger.info(f"roam_file: {roam_file}")

        # Read the expected JPEG file
        with open("tests/fixtures/images/flower.jpeg", "rb") as f:
            expected_contents: bytes = f.read()

        # Assert the fetched file matches the expected file
        assert roam_file.file_name == "flower.jpeg"
        assert roam_file.contents == expected_contents
        assert roam_file.media_type == "image/jpeg"
        assert isinstance(roam_file.last_modified, datetime)
