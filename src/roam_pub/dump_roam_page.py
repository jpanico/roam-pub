#!/usr/bin/env python3
"""Script to dump a Roam Research page as a Rich tree to the console.

Fetches all descendant blocks of a given page and renders them as a
formatted tree in the terminal.

Example:
    dump-roam-page "Test Article" -p 3333 -g SCFH -t your-bearer-token
"""

import logging
from typing import Annotated

import typer
from rich.console import Console
from rich.tree import Tree as RichTree

from roam_pub.rich import DEFAULT_PANEL_PROPS, build_rich_tree
from roam_pub.roam_local_api import ApiEndpoint
from roam_pub.roam_node import RoamNode
from roam_pub.roam_node_fetch import FetchRoamNodes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] (%(module)s.%(funcName)s:%(lineno)d) %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

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
    props: Annotated[
        str | None,
        typer.Option(
            "--props",
            help=(
                "Comma-separated list of RoamNode property names to include in each panel body. "
                f"Example: --props heading,parents. "
                f"Defaults to: {','.join(DEFAULT_PANEL_PROPS)}."
            ),
        ),
    ] = None,
) -> None:
    """Dump a Roam Research page as a Rich tree to the console.

    Fetches all descendant blocks of PAGE_TITLE and renders them as a
    formatted tree in the terminal.
    """
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
        [p.strip() for p in props.split(",")] if props is not None else list(DEFAULT_PANEL_PROPS)
    )
    trees: list[RichTree] = build_rich_tree(nodes, effective_props)

    console: Console = Console()
    for tree in trees:
        console.print(tree)


if __name__ == "__main__":
    app()
