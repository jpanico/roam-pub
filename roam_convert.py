#!/usr/bin/env python3
"""Convert Roam Research Markdown to standard Markdown with headers."""

import argparse
import re
from pathlib import Path
from re import Match


def convert_roam_markdown(input_path: Path) -> str:
    """Convert Roam Research Markdown to standard Markdown.

    - Adds H1 with the original filename
    - Converts root-level bullets to H2 headers
    """
    content: str = input_path.read_text()
    lines: list[str] = content.splitlines()
    output_lines: list[str] = []

    # Add H1 with filename (without extension)
    output_lines.append(f"# {input_path.stem}")
    output_lines.append("")

    for line in lines:
        # Match root-level bullets (no leading whitespace)
        # Roam uses "- " for bullets
        match: Match[str] | None = re.match(r'^- (.+)$', line)
        if match:
            # Convert to H2
            output_lines.append(f"## {match.group(1)}")
        else:
            output_lines.append(line)

    return "\n".join(output_lines)


def main() -> int:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Convert Roam Research Markdown to standard Markdown"
    )
    parser.add_argument("input_file", type=Path, help="Path to input Markdown file")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (default: input_converted.md)"
    )
    args: argparse.Namespace = parser.parse_args()

    input_path: Path = args.input_file
    if not input_path.exists():
        print(f"Error: {input_path} does not exist")
        return 1

    output_path: Path | None = args.output
    if output_path is None:
        output_path = input_path.with_stem(f"{input_path.stem}_converted")

    converted: str = convert_roam_markdown(input_path)
    output_path.write_text(converted)
    print(f"Converted: {input_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
