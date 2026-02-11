from string import Template
from typing import ClassVar, Final
from pydantic import BaseModel
import requests
import json
import base64


class ApiEndpointURL(BaseModel):
    """
    Pydantic ensures that `local_api_port` and `graph_name` are required and non-null by default
    """

    local_api_port: int
    graph_name: str

    SCHEME: ClassVar[Final[str]] = "http"
    HOST: ClassVar[Final[str]] = "127.0.0.1"
    API_PATH_STEM: ClassVar[Final[str]] = "/api/"

    def __str__(self):
        return f"{self.SCHEME}://{self.HOST}:{self.local_api_port}{self.API_PATH_STEM}{self.graph_name}"


class FetchRoamFile:
    HEADERS: Final[str] = """
    {
        "Content-Type": "application/json"
    }
    """
    PAYLOAD_TEMPLATE: Final[str] = """
    {
       "action": "file.get",
        "args": [
            {
                "url" : "{file_url}",
                "format": "base64"
            }
        ]
    }
    """

    @staticmethod
    def fetch(api_endpoint: ApiEndpointURL, file_url: str) -> str:
        """
        Fetch a file from Roam Research API.

        Args:
            api_endpoint: The API endpoint URL (validated by Pydantic)
            file_url: The file URL to fetch (required, non-empty)

        Returns:
            The local filename where the file was saved

        Raises:
            ValueError: If file_url is None or empty
            requests.exceptions.ConnectionError: If unable to connect to API
            requests.exceptions.HTTPError: If API returns error status
        """
        # Validate file_url is not None or empty
        if not file_url or not file_url.strip():
            raise ValueError("file_url cannot be None or empty")

        headers: dict = {"Content-Type": "application/json"}

        payload: dict = {
            "action": "file.get",
            "args": [{"url": file_url, "format": "base64"}],
        }

        print(f"Requesting file from: {api_endpoint}")

        # The Local API expects a POST request with the file URL
        response: requests.Response = requests.post(
            str(api_endpoint), json=payload, headers=headers, stream=False
        )

        if response.status_code == 200:
            response_payload: dict = json.loads(response.text)
            payload_result: dict = response_payload["result"]
            file_bytes: bytes = base64.b64decode(payload_result["base64"])
            file_name: str = payload_result["filename"]

            # Write binary data to file
            with open(file_name, "wb") as file:
                file.write(file_bytes)

            print(f"Success! File saved to: {file_name}")
            return file_name
        else:
            error_msg: str = (
                f"Failed to fetch file. Status Code: {response.status_code}, Response: {response.text}"
            )
            raise requests.exceptions.HTTPError(error_msg)


def fetch_roam_file(local_api_port, graph_name, file_url):
    """
    Fetches a file from Roam Research via the Local API (handles decryption).

    Args:
        local_api_port (int): The port shown in Roam Desktop > Settings > Local API.
        graph_name (str): The name of your Roam graph.
        file_url (str): The Firebase storage URL (e.g., https://firebasestorage...).
    """

    # The Local API endpoint for file fetching
    api_endpoint: str = f"http://127.0.0.1:{local_api_port}/api/{graph_name}"

    headers: dict = {"Content-Type": "application/json"}

    payload: dict = {
        "action": "file.get",
        "args": [{"url": file_url, "format": "base64"}],
    }

    print(f"Requesting file from: {api_endpoint}")

    try:
        # The Local API expects a POST request with the file URL
        response: requests.Response = requests.post(
            api_endpoint, json=payload, headers=headers, stream=False
        )

        if response.status_code == 200:
            response_payload: dict = json.loads(response.text)
            payload_result: dict = response_payload["result"]
            file_bytes: bytes = base64.b64decode(payload_result["base64"])
            file_name: str = payload_result["filename"]
            # 'wb' stands for Write Binary
            with open(file_name, "wb") as file:
                file.write(file_bytes)

            print(f"Success! File saved to: {file_name}")
        else:
            print(f"Error: Failed to fetch file. Status Code: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print(
            "Error: Could not connect to Roam Local API. Is the Roam Desktop App running and Local API enabled?"
        )


# --- Configuration ---
# 1. Open Roam Desktop -> Settings -> Graph -> Local API to find your PORT.
PORT = 3333  # Replace with your actual port
GRAPH = "SCFH"
# 2. The URL usually found in a block like ![](https://firebasestorage...)
FILE_URL = "https://firebasestorage.googleapis.com/v0/b/firescript-577a2.appspot.com/o/imgs%2Fapp%2FSCFH%2F-9owRBegJ8.jpeg.enc?alt=media&token=9b673aae-8089-4a91-84df-9dac152a7f94"

# --- Execute ---
if __name__ == "__main__":
    fetch_roam_file(PORT, GRAPH, FILE_URL)
