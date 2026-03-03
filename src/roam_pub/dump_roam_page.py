#!/usr/bin/env python3
"""CLI tool for dumping a Roam Research page as a Rich tree to the terminal.

Fetches all descendant blocks of a named page via the Roam Local API and
renders them as a colorized :class:`~rich.tree.Tree` panel hierarchy.  Each
block is displayed as a panel whose body lists selected
:class:`~roam_pub.roam_node.RoamNode` fields, configurable via ``--node-props``
(defaults to :data:`~roam_pub.rich.DEFAULT_PANEL_PROPS`).

Logging is colorized by level via :mod:`roam_pub.logging_config` and
configurable via the ``LOG_LEVEL`` environment variable (default: ``INFO``).

Public symbols:

- :data:`app` — the :class:`~typer.Typer` application instance.
- :func:`main` — the CLI entry point; registered as the ``dump-roam-page``
  console script.

Example::

    dump-roam-page "Test Article" -p 3333 -g SCFH -t your-bearer-token
    dump-roam-page "Test Article" -p 3333 -g SCFH -t tok --node-props heading,parents
"""

import enum
import logging
from typing import Annotated

import typer
from rich.console import Console
from rich.tree import Tree as RichTree

from roam_pub.rich import DEFAULT_PANEL_PROPS, build_rich_node_tree, build_rich_vertex_tree
from roam_pub.roam_graph import VertexTree
from roam_pub.roam_local_api import ApiEndpoint
from roam_pub.logging_config import configure_logging
from roam_pub.roam_node import NodeTree, RoamNode
from roam_pub.roam_node_fetch import FetchRoamNodes
from roam_pub.roam_transcribe import transcribe

configure_logging()
logger = logging.getLogger(__name__)


class Mode(enum.StrEnum):
    """Output mode controlling which tree(s) are printed to the console."""

    vertex = "v"
    node = "n"
    both = "vn"


app = typer.Typer()


@app.command()
def main(
    page_title: Annotated[str, typer.Argument(help="The title of a Roam Page")],
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
                f"Defaults to: {','.join(DEFAULT_PANEL_PROPS)}."
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
    """Dump a Roam Research page as a Rich tree to the console.

    Fetches all descendant blocks of PAGE_TITLE and renders them as a
    formatted tree in the terminal.
    """
    logger.debug(
        "page_title=%r, local_api_port=%r, graph_name=%r, api_bearer_token=%r, node_props=%r, mode=%r",
        page_title,
        local_api_port,
        graph_name,
        api_bearer_token,
        node_props,
        mode,
    )
    api_endpoint: ApiEndpoint = ApiEndpoint.from_parts(
        local_api_port=local_api_port,
        graph_name=graph_name,
        bearer_token=api_bearer_token,
    )

    try:
        nodes: list[RoamNode] = FetchRoamNodes.fetch_by_page_title(page_title=page_title, api_endpoint=api_endpoint)
    except Exception as e:
        logger.error(f"Error fetching page '{page_title}': {e}")
        raise typer.Exit(code=1)

    effective_props: list[str] = (
        [p.strip() for p in node_props.split(",")] if node_props is not None else list(DEFAULT_PANEL_PROPS)
    )
    node_tree: NodeTree = NodeTree(network=nodes)
    vertex_tree: VertexTree = transcribe(node_tree)
    logger.debug("vertex_tree=%r", vertex_tree)
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


if __name__ == "__main__":
    app()
