from datetime import datetime
from string import Template
from typing import ClassVar, Final
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
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


class FetchRoamAsset:
    REQUEST_HEADERS: Final[dict] = {"Content-Type": "application/json"}
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
    def roam_file_from_response_text(response_text: str) -> RoamAsset:
        logger.debug(f"response_text: {response_text}")
        if response_text is None:
            raise TypeError("response_text cannot be None")

        response_payload: dict = json.loads(response_text)
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
    def fetch(api_endpoint: ApiEndpointURL, firebase_url: HttpUrl) -> RoamAsset:
        """
        Fetch an asset (file) from Roam Research **Local** API. Because this goes through the Local API, the Roam Research
        native App must be running at the time this method is called, and the user must be logged into the graph having 
        `graph_name`

        Args:
            api_endpoint: The API endpoint URL (validated by Pydantic)
            firebase_url: The Firebase URL that appears in Roam Markdown

        Returns:
            RoamAsset object containing the fetched file data

        Raises:
            TypeError: If api_endpoint or file_url is None
            requests.exceptions.ConnectionError: If unable to connect to API
            requests.exceptions.HTTPError: If API returns error status
        """

        logger.debug(f"api_endpoint: {api_endpoint}, firebase_url: {firebase_url}")
        if api_endpoint is None:
            raise TypeError("api_endpoint cannot be None")
        if firebase_url is None:
            raise TypeError("file_url cannot be None")

        request_payload_str: str = FetchRoamAsset.REQUEST_PAYLOAD_TEMPLATE.substitute(file_url=firebase_url)
        request_payload: dict = json.loads(request_payload_str)
        logger.info(
            f"request_payload: {request_payload}, headers: {FetchRoamAsset.REQUEST_HEADERS}, api: {api_endpoint}"
        )

        # The Local API expects a POST request with the file URL
        response: requests.Response = requests.post(
            str(api_endpoint), json=request_payload, headers=FetchRoamAsset.REQUEST_HEADERS, stream=False
        )

        if response.status_code == 200:
            return FetchRoamAsset.roam_file_from_response_text(response.text)
        else:
            error_msg: str = f"Failed to fetch file. Status Code: {response.status_code}, Response: {response.text}"
            logger.error(error_msg)
            raise requests.exceptions.HTTPError(error_msg)
