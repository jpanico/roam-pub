"""Roam Research node-fetch result types.

Public symbols:

- :class:`QueryAnchorKind` — enum discriminating a page-title target from a node-UID target.
- :class:`NodeFetchAnchor` — immutable model pairing a raw anchor string with its detected kind.
- :data:`NodeFetchResult` — flat list of :class:`~roam_pub.roam_node.RoamNode` records
  returned by all :class:`~roam_pub.roam_node_fetch.FetchRoamNodes` fetch methods.
"""

import enum

from pydantic import BaseModel, ConfigDict, Field, computed_field

from roam_pub.roam_node import RoamNode
from roam_pub.roam_primitives import UID_RE


@enum.unique
class QueryAnchorKind(enum.Enum):
    """Discriminates the kind of anchor passed to :class:`~roam_pub.roam_node_fetch.FetchRoamNodes` fetch methods.

    Attributes:
        PAGE_TITLE: The anchor is a Roam page title string.
        NODE_UID: The anchor is a nine-character ``:block/uid`` string.
    """

    PAGE_TITLE = enum.auto()
    NODE_UID = enum.auto()

    @staticmethod
    def of(anchor: str) -> QueryAnchorKind:
        """Return the :class:`QueryAnchorKind` for *anchor*.

        Args:
            anchor: A Roam page title or nine-character node UID.

        Returns:
            :attr:`NODE_UID` when *anchor* matches
            :data:`~roam_pub.roam_primitives.UID_RE`; :attr:`PAGE_TITLE` otherwise.
        """
        return QueryAnchorKind.NODE_UID if UID_RE.match(anchor) else QueryAnchorKind.PAGE_TITLE


class NodeFetchAnchor(BaseModel):
    """Immutable model pairing a raw anchor string with its derived :class:`QueryAnchorKind`.

    Attributes:
        target: The raw anchor string — either a Roam page title or a nine-character node UID.
        kind: Derived from *target* via :meth:`QueryAnchorKind.of`.
    """

    model_config = ConfigDict(frozen=True)

    target: str = Field(description="A Roam page title or nine-character node UID.")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def kind(self) -> QueryAnchorKind:
        """Derive the :class:`QueryAnchorKind` from :attr:`target`."""
        return QueryAnchorKind.of(self.target)


type NodeFetchResult = list[RoamNode]
"""Flat list of :class:`~roam_pub.roam_node.RoamNode` records returned by all public fetch methods."""
