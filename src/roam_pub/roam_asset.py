from datetime import datetime
from string import Template
from typing import ClassVar, Final, final
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, validate_call
import requests
import json
import base64
import logging

logger = logging.getLogger(__name__)


class ApiEndpointURL(BaseModel):
    """
    Immutable API endpoint URL for Roam Research Local API.

    Pydantic ensures that `local_api_port` and `graph_name` are required and non-null by default.
    Once created, instances cannot be modified (frozen).
    """

    model_config = ConfigDict(frozen=True)

    local_api_port: int
    graph_name: str

    SCHEME: ClassVar[Final[str]] = "http"
    HOST: ClassVar[Final[str]] = "127.0.0.1"
    API_PATH_STEM: ClassVar[Final[str]] = "/api/"

    def __str__(self):
        return f"{self.SCHEME}://{self.HOST}:{self.local_api_port}{self.API_PATH_STEM}{self.graph_name}"


class RoamAsset(BaseModel):
    """
    Roam uploads all user assets (files, media) to Firebase, and stores only Firebase locators (URLS) within the Roam graph DB
    itself (nodes). This class is an immutable representation of an asset that is fetched from Firebase *through*
    the Roam api.

    Once created, instances cannot be modified (frozen). All fields are required
    and validated at construction time.
    """

    model_config = ConfigDict(frozen=True)

    file_name: str = Field(..., min_length=1, description="Name of the file")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    media_type: str = Field(..., pattern=r"^[\w-]+/[\w-]+$", description="MIME type (e.g., 'image/jpeg')")
    contents: bytes = Field(..., description="Binary file contents")


@final
class FetchRoamAsset:
    """
    Stateless utility class for fetching Roam assets from the Roam Research Local API.

    Class Attributes:
        REQUEST_HEADERS: HTTP headers used for all API requests
        REQUEST_PAYLOAD_TEMPLATE: JSON template for building request payloads.
            Contains the action 'file.get' and expects a $file_url substitution
            parameter for the Firebase URL. The format parameter is set to 'base64' to receive binary
            data in base64-encoded format.
    """

    def __init__(self):
        raise TypeError("FetchRoamAsset is a stateless utility class and cannot be instantiated")

    REQUEST_HEADERS_TEMPLATE: Final[Template] = Template("""
    {
        "Content-Type": "application/json",
        "Authorization": "Bearer $roam_local_api_token"
    }
    """)

    REQUEST_PAYLOAD_TEMPLATE: Final[Template] = Template("""
    {
       "action": "file.get",
        "args": [
            {
                "url" : "$file_url",
                "format": "base64"
            }
        ]
    }
    """)

    @staticmethod
    @validate_call
    def roam_file_from_response_json(response_json: str) -> RoamAsset:
        logger.debug(f"response_json: {response_json}")

        response_payload: dict = json.loads(response_json)
        payload_result: dict = response_payload["result"]
        file_bytes: bytes = base64.b64decode(payload_result["base64"])
        file_name: str = payload_result["filename"]
        media_type: str = payload_result["mimetype"]

        logger.info(f"Successfully fetched file: {file_name}")

        # Return RoamAsset object
        return RoamAsset(
            file_name=file_name,
            last_modified=datetime.now(),
            media_type=media_type,
            contents=file_bytes,
        )

    @staticmethod
    @validate_call
    def fetch(api_endpoint: ApiEndpointURL, api_bearer_token: str, firebase_url: HttpUrl) -> RoamAsset:
        """
        Fetch an asset (file) from Roam Research **Local** API. Because this goes through the Local API, the Roam Research
        native App must be running at the time this method is called, and the user must be logged into the graph having
        `graph_name`

        Args:
            api_endpoint: The API endpoint URL (validated by Pydantic)
            api_bearer_token: The bearer token for authenticating with the Roam Local API
            firebase_url: The Firebase URL that appears in Roam Markdown

        Returns:
            RoamAsset object containing the fetched file data

        Raises:
            ValidationError: If any parameter is None or invalid
            requests.exceptions.ConnectionError: If unable to connect to API
            requests.exceptions.HTTPError: If API returns error status
        """

        logger.debug(f"api_endpoint: {api_endpoint}, firebase_url: {firebase_url}")

        request_headers_str: str = FetchRoamAsset.REQUEST_HEADERS_TEMPLATE.substitute(
            roam_local_api_token=api_bearer_token
        )
        request_headers: dict = json.loads(request_headers_str)
        request_payload_str: str = FetchRoamAsset.REQUEST_PAYLOAD_TEMPLATE.substitute(file_url=firebase_url)
        request_payload: dict = json.loads(request_payload_str)
        logger.info(f"request_payload: {request_payload}, headers: {request_headers}, api: {api_endpoint}")

        # The Local API expects a POST request with the file URL
        response: requests.Response = requests.post(
            str(api_endpoint), json=request_payload, headers=request_headers, stream=False
        )

        if response.status_code == 200:
            return FetchRoamAsset.roam_file_from_response_json(response.text)
        else:
            error_msg: str = f"Failed to fetch file. Status Code: {response.status_code}, Response: {response.text}"
            logger.error(error_msg)
            raise requests.exceptions.HTTPError(error_msg)
