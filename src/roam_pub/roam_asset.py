"""Roam Research asset data model.

Public symbols:

- :data:`FIRESTORE_IMAGE_RE` — compiled regex matching a Roam markdown image link whose URL
  is a Cloud Firestore storage URL.
- :class:`RoamAsset` — immutable representation of an asset fetched from Cloud Firestore
  through the Roam API.
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from roam_pub.roam_types import MediaType

FIRESTORE_IMAGE_RE: re.Pattern[str] = re.compile(
    r"!\[(?P<alt>(?:[^\]]|\n)*?)\]\((?P<url>https://firebasestorage\.googleapis\.com/[^\)]+)\)"
)
"""Compiled regex matching a Roam markdown image link whose URL is a Cloud Firestore storage URL.

Named groups:

- ``alt`` — the alt-text content between ``[`` and ``]`` (may be empty or multi-line).
- ``url`` — the Cloud Firestore storage URL between ``(`` and ``)``.

Example match on ``![my photo](https://firebasestorage.googleapis.com/v0/b/...)``:

- ``match.group(0)`` — the full ``![...](..)`` string.
- ``match.group("url")`` — just the URL.
- ``match.group("alt")`` — just the alt text.
"""


class RoamAsset(BaseModel):
    """Immutable representation of an asset fetched from Cloud Firestore through the Roam API.

    Roam uploads all user assets (files, media) to Cloud Firestore, and stores only Cloud Firestore
    locators (URLs) within the Roam graph DB itself (nodes).

    Once created, instances cannot be modified (frozen). All fields are required
    and validated at construction time.
    """

    model_config = ConfigDict(frozen=True)

    file_name: str = Field(..., min_length=1, description="Name of the file")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    media_type: MediaType = Field(..., description="MIME type (e.g., 'image/jpeg')")
    contents: bytes = Field(..., description="Binary file contents")
