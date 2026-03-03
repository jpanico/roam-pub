#!/usr/bin/env python3
"""CLI tool for dumping a Roam Research page as a Rich tree to the terminal.

Fetches all descendant blocks of a named page via the Roam Local API and
renders them as a colorized :class:`~rich.tree.Tree` panel hierarchy.  Each
block is displayed as a panel whose body lists selected
:class:`~roam_pub.roam_node.RoamNode` fields, configurable via ``--props``
(defaults to :data:`~roam_pub.rich.DEFAULT_PANEL_PROPS`).

Logging is colorized by level and configurable via the ``LOG_LEVEL``
environment variable (default: ``INFO``).

Public symbols:

- :data:`app` — the :class:`~typer.Typer` application instance.
- :func:`main` — the CLI entry point; registered as the ``dump-roam-page``
  console script.

Example::

    dump-roam-page "Test Article" -p 3333 -g SCFH -t your-bearer-token
    dump-roam-page "Test Article" -p 3333 -g SCFH -t tok --props heading,parents
"""

import logging
import os
import re
from typing import Annotated, TextIO

import typer
from rich.console import Console
from rich.tree import Tree as RichTree

from roam_pub.rich import DEFAULT_PANEL_PROPS, build_rich_trees
from roam_pub.roam_local_api import ApiEndpoint
from roam_pub.roam_node import RoamNode
from roam_pub.roam_node_fetch import FetchRoamNodes

_LEVEL_COLORS: dict[str, str] = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[1;31m",
}
_LOCATION_COLOR: str = "\033[35m"  # magenta — distinct from all level colors
_COLOR_RESET: str = "\033[0m"

_MESSAGE_HIGHLIGHTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\s*id=\d+,"), "\033[1;97m"),  # bold bright white
]


def _highlight_message(message: str) -> str:
    """Return *message* with all :data:`_MESSAGE_HIGHLIGHTS` patterns ANSI-colorized."""
    for pattern, color in _MESSAGE_HIGHLIGHTS:
        message = pattern.sub(lambda m, c=color: f"{c}{m.group()}{_COLOR_RESET}", message)
    return message


class _ColorLevelFormatter(logging.Formatter):
    """Formatter that ANSI-colorizes the levelname, call-site location, and message highlights."""

    def format(self, record: logging.LogRecord) -> str:
        """Format *record*, colorizing levelname, module::funcName location, and message highlights."""
        color = _LEVEL_COLORS.get(record.levelname, "")
        original_levelname = record.levelname
        original_msg = record.msg
        original_args = record.args
        record.levelname = f"{color}[{record.levelname}]{_COLOR_RESET}"
        setattr(record, "location", f"{_LOCATION_COLOR}({record.module}::{record.funcName}){_COLOR_RESET}")
        record.msg = _highlight_message(record.getMessage())
        record.args = None
        result = super().format(record)
        record.levelname = original_levelname
        record.msg = original_msg
        record.args = original_args
        delattr(record, "location")
        return result


_handler: logging.StreamHandler[TextIO] = logging.StreamHandler()
_handler.setFormatter(
    _ColorLevelFormatter(
        fmt="%(asctime)s %(levelname)s %(location)s %(message)s",
        datefmt="%H:%M:%S",
    )
)
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    handlers=[_handler],
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
    logger.debug(
        "page_title=%r, local_api_port=%r, graph_name=%r, api_bearer_token=%r, props=%r",
        page_title,
        local_api_port,
        graph_name,
        api_bearer_token,
        props,
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
        [p.strip() for p in props.split(",")] if props is not None else list(DEFAULT_PANEL_PROPS)
    )
    trees: list[RichTree] = build_rich_trees(nodes, effective_props)

    console: Console = Console()
    for tree in trees:
        console.print(tree)


if __name__ == "__main__":
    app()
