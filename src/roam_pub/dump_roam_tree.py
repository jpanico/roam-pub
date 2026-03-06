#!/usr/bin/env python3
"""CLI tool for dumping a Roam Research page or node subtree as a Rich tree to the terminal.

Fetches all descendant blocks identified by ``TARGET`` via the Roam Local API,
transcribes them into a :class:`~roam_pub.roam_graph.VertexTree`, and renders
one or both of the following as a colorized :class:`~rich.tree.Tree` panel
hierarchy:

- **Vertex tree** (default, ``--mode v``) — normalized
  :class:`~roam_pub.roam_graph.VertexTree` produced by
  :func:`~roam_pub.roam_transcribe.transcribe`.
- **Node tree** (``--mode n``) — raw :class:`~roam_pub.roam_node.NodeTree`
  as returned by the Roam Local API; each panel body lists selected
  :class:`~roam_pub.roam_node.RoamNode` fields, configurable via
  ``--node-props`` (defaults to
  :data:`~roam_pub.rich.DEFAULT_NODE_PANEL_PROPS`).
- **Both** (``--mode vn``) — vertex tree followed by node tree.

``TARGET`` is interpreted as a **node UID** if it matches
:data:`~roam_pub.roam_primitives.UID_PATTERN` (exactly 9 alphanumeric/dash/underscore
characters, the fixed format used by Roam for all block and page UIDs); otherwise it is
treated as a **page title**.  A page whose title happens to be exactly 9
characters from that alphabet would be misidentified — this edge case is
considered negligible in practice.

Logging is colorized by level via :mod:`roam_pub.logging_config` and
configurable via the ``LOG_LEVEL`` environment variable (default: ``INFO``).

Public symbols:

- :class:`Mode` — ``StrEnum`` of output modes: ``v`` (vertex), ``n`` (node),
  ``vn`` (both).
- :func:`dump_trees` — renders and prints a flat node list as Rich tree(s) to
  the console.
- :data:`app` — the :class:`~typer.Typer` application instance.
- :func:`main` — the CLI entry point; registered as the ``dump-roam-tree``
  console script.

Example::

    dump-roam-tree "Test Article" -p 3333 -g SCFH -t your-bearer-token
    dump-roam-tree wdMgyBiP9 -p 3333 -g SCFH -t tok
    dump-roam-tree "Test Article" -p 3333 -g SCFH -t tok --mode n --node-props heading,parents
"""

import enum
import logging
from typing import Annotated, Final

import typer
from rich.console import Console
from rich.tree import Tree as RichTree

from roam_pub.rich import DEFAULT_NODE_PANEL_PROPS, build_rich_node_tree, build_rich_vertex_tree
from roam_pub.roam_tree_loader import fetch_roam_trees
from roam_pub.roam_graph import VertexTree
from roam_pub.roam_local_api import ApiEndpoint
from roam_pub.logging_config import configure_logging
from roam_pub.roam_node import NodeTree
from roam_pub.roam_primitives import UID_PATTERN

configure_logging()
logger = logging.getLogger(__name__)


class Mode(enum.StrEnum):
    """Output mode controlling which tree(s) are printed to the console."""

    vertex = "v"
    node = "n"
    both = "vn"


app = typer.Typer()


def dump_trees(node_tree: NodeTree, vertex_tree: VertexTree, node_props: str | None, mode: Mode) -> None:
    """Render and print a Roam node tree as Rich tree(s) to the console.

    Prints the vertex tree, the raw node tree, or both, depending on *mode*.

    Args:
        node_tree: Raw :class:`~roam_pub.roam_node.NodeTree` as returned by the
            Roam Local API.
        vertex_tree: Normalized :class:`~roam_pub.roam_graph.VertexTree` produced
            by :func:`~roam_pub.roam_transcribe.transcribe`.
        node_props: Comma-separated list of :class:`~roam_pub.roam_node.RoamNode`
            field names to include in each node panel body, or ``None`` to use
            :data:`~roam_pub.rich.DEFAULT_NODE_PANEL_PROPS`.
        mode: Which tree(s) to print — vertex only, node only, or both.
    """
    effective_props: list[str] = (
        [p.strip() for p in node_props.split(",")] if node_props is not None else list(DEFAULT_NODE_PANEL_PROPS)
    )
    node_rich_tree: RichTree = build_rich_node_tree(node_tree, effective_props)
    vertex_rich_tree: RichTree = build_rich_vertex_tree(vertex_tree)
    logger.debug("vertex_rich_tree=%r", vertex_rich_tree)

    console: Console = Console()
    if mode in (Mode.vertex, Mode.both):
        console.rule("[bold]Vertex Tree[/bold]")
        console.print()
        console.print(vertex_rich_tree)
    if mode in (Mode.node, Mode.both):
        console.rule("[bold]Node Tree[/bold]")
        console.print()
        console.print(node_rich_tree)
        console.print()


@app.command()
def main(
    target: Annotated[
        str,
        typer.Argument(
            help=(
                "Roam page title or node UID to dump. "
                f"Treated as a node UID if it matches {UID_PATTERN}; "
                "otherwise treated as a page title."
            ),
        ),
    ],
    local_api_port: Annotated[
        int,
        typer.Option(
            "--port",
            "-p",
            envvar="ROAM_LOCAL_API_PORT",
            help="Port for Roam Local API",
        ),
    ],
    graph_name: Annotated[
        str,
        typer.Option(
            "--graph",
            "-g",
            envvar="ROAM_GRAPH_NAME",
            help="Name of the Roam graph",
        ),
    ],
    api_bearer_token: Annotated[
        str,
        typer.Option(
            "--token",
            "-t",
            envvar="ROAM_API_TOKEN",
            help="Bearer token for Roam Local API authentication",
        ),
    ],
    node_props: Annotated[
        str | None,
        typer.Option(
            "--node-props",
            help=(
                "Comma-separated list of RoamNode property names to include in each panel body. "
                f"Example: --node-props heading,parents. "
                f"Defaults to: {','.join(DEFAULT_NODE_PANEL_PROPS)}."
            ),
        ),
    ] = None,
    mode: Annotated[
        Mode,
        typer.Option(
            "--mode",
            help="Output mode: v=vertex tree only, n=node tree only, vn=both.",
        ),
    ] = Mode.vertex,
) -> None:
    """Dump a Roam Research page or node subtree as a Rich tree to the console.

    TARGET is interpreted as a node UID (fetches the subtree rooted there) if
    it matches :data:`~roam_pub.roam_primitives.UID_PATTERN`, otherwise as a
    page title (fetches all blocks on that page).  Renders the vertex tree, the
    raw node tree, or both, depending on ``--mode`` (default: vertex tree only).
    """
    logger.debug(
        "target=%r, local_api_port=%r, graph_name=%r, api_bearer_token=%r, node_props=%r, mode=%r",
        target,
        local_api_port,
        graph_name,
        api_bearer_token,
        node_props,
        mode,
    )
    api_endpoint: Final[ApiEndpoint] = ApiEndpoint.from_parts(
        local_api_port=local_api_port,
        graph_name=graph_name,
        bearer_token=api_bearer_token,
    )

    trees: Final[tuple[NodeTree, VertexTree]] = fetch_roam_trees(target, api_endpoint)
    node_tree: Final[NodeTree] = trees[0]
    vertex_tree: Final[VertexTree] = trees[1]
    dump_trees(node_tree=node_tree, vertex_tree=vertex_tree, node_props=node_props, mode=mode)


if __name__ == "__main__":
    app()
