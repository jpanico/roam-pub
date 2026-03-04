#!/usr/bin/env python3
"""CLI tool for exporting a Roam Research page to a CommonMark document.

Fetches all descendant blocks of a named page via the Roam Local API,
transcribes them into a :class:`~roam_pub.roam_graph.VertexTree`, renders
the tree to a CommonMark document via
:func:`~roam_pub.roam_render_md.render`, and writes the result to
``<output_dir>/<page_title>.md``.

Logging is colorized by level via :mod:`roam_pub.logging_config` and
configurable via the ``LOG_LEVEL`` environment variable (default: ``INFO``).

Public symbols:

- :data:`app` — the :class:`~typer.Typer` application instance.
- :func:`main` — the CLI entry point; registered as the ``export-roam-page``
  console script.

Example::

    export-roam-page "Test Article" -p 3333 -g SCFH -t your-bearer-token -o ~/docs
    export-roam-page "Test Article"  # reads all options from env vars
"""

import logging
import pathlib
from typing import Annotated

import typer

from roam_pub.logging_config import configure_logging
from roam_pub.roam_graph import VertexTree
from roam_pub.roam_local_api import ApiEndpoint
from roam_pub.roam_node import NodeTree, RoamNode
from roam_pub.roam_node_fetch import FetchRoamNodes
from roam_pub.roam_render_md import render
from roam_pub.roam_transcribe import transcribe

configure_logging()
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
    output_dir: Annotated[
        pathlib.Path,
        typer.Option(
            "--output-dir",
            "-o",
            envvar="ROAM_EXPORT_DIR",
            help="Directory to write the exported CommonMark document into.",
        ),
    ],
) -> None:
    """Export a Roam Research page to a CommonMark document.

    Fetches all descendant blocks of PAGE_TITLE, transcribes them into a
    normalized VertexTree, renders the tree to CommonMark, and writes the
    result to OUTPUT_DIR/<page_title>.md.
    """
    logger.debug(
        "page_title=%r, local_api_port=%r, graph_name=%r, api_bearer_token=%r, output_dir=%r",
        page_title,
        local_api_port,
        graph_name,
        api_bearer_token,
        output_dir,
    )
    api_endpoint: ApiEndpoint = ApiEndpoint.from_parts(
        local_api_port=local_api_port,
        graph_name=graph_name,
        bearer_token=api_bearer_token,
    )

    try:
        nodes: list[RoamNode] = FetchRoamNodes.fetch_by_page_title(page_title=page_title, api_endpoint=api_endpoint)
    except Exception as e:
        logger.error("Error fetching page %r: %s", page_title, e)
        raise typer.Exit(code=1)

    node_tree: NodeTree = NodeTree(network=nodes)
    vertex_tree: VertexTree = transcribe(node_tree)
    logger.debug("vertex_tree=%r", vertex_tree)

    md_document: str = render(vertex_tree)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path: pathlib.Path = output_dir / f"{page_title}.md"
    output_path.write_text(md_document)
    logger.info("Wrote CommonMark document to %s", output_path)


if __name__ == "__main__":
    app()
