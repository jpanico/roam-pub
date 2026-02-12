#!/usr/bin/env python3
"""Convert Roam Research Markdown to standard Markdown or PDF."""

import argparse
import re
from pathlib import Path
from re import Match
from typing import Literal

OutputFormat = Literal["md", "pdf"]


def unindent_line(line: str) -> str:
    """Remove one level of indentation from a line.

    Handles both tabs and spaces (4 spaces = 1 level).
    """
    if line.startswith("\t"):
        return line[1:]
    if line.startswith("    "):
        return line[4:]
    return line


def is_double_brace_line(line: str) -> bool:
    """Check if line content is enclosed in double braces {{...}}.

    Handles lines with leading whitespace and bullet markers.
    """
    # Strip whitespace and bullet marker to get content
    content: str = line.strip()
    if content.startswith("- "):
        content = content[2:]
    return content.startswith("{{") and content.endswith("}}")


def convert_roam_markdown(input_path: Path) -> str:
    """Convert Roam Research Markdown to standard Markdown.

    - Adds H1 with the original filename
    - Converts root-level bullets to H2 headers
    - Unindents all lines by one level
    - Removes lines enclosed in double braces {{...}}
    """
    content: str = input_path.read_text()
    lines: list[str] = content.splitlines()
    output_lines: list[str] = []

    # Add H1 with filename (without extension)
    output_lines.append(f"# {input_path.stem}")
    output_lines.append("")

    for line in lines:
        # Skip lines with content enclosed in double braces
        if is_double_brace_line(line):
            continue

        # Match root-level bullets (no leading whitespace)
        # Roam uses "- " for bullets
        match: Match[str] | None = re.match(r"^- (.+)$", line)
        if match:
            # Convert to H2
            output_lines.append(f"## {match.group(1)}")
        else:
            # Unindent non-header lines by one level
            output_lines.append(unindent_line(line))

    return "\n".join(output_lines)


def markdown_to_pdf(markdown_content: str, output_path: Path) -> None:
    """Convert markdown content to PDF using panflute/pandoc."""
    import shutil
    import subprocess
    import tempfile

    import panflute

    # Find an available PDF engine
    pdf_engines: list[str] = [
        "tectonic",
        "xelatex",
        "lualatex",
        "pdflatex",
        "wkhtmltopdf",
        "weasyprint",
        "prince",
    ]

    # Also check common Homebrew/MacPorts paths
    extra_paths: list[str] = [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/opt/local/bin",
    ]

    available_engine: str | None = None
    for engine in pdf_engines:
        # Check PATH first
        engine_path: str | None = shutil.which(engine)
        if engine_path:
            available_engine = engine_path
            break
        # Check extra paths
        for prefix in extra_paths:
            full_path: str = f"{prefix}/{engine}"
            if Path(full_path).exists():
                available_engine = full_path
                break
        if available_engine:
            break

    if available_engine is None:
        raise RuntimeError(
            "No PDF engine found. Install one of: tectonic, xelatex, "
            "lualatex, pdflatex, wkhtmltopdf, weasyprint, or prince.\n"
            "On macOS: brew install tectonic"
        )

    # LaTeX header to support deeply nested lists
    latex_header: str = r"""
\usepackage{enumitem}
\setlistdepth{9}
\setlist[itemize,1]{label=\textbullet}
\setlist[itemize,2]{label=\textbullet}
\setlist[itemize,3]{label=\textbullet}
\setlist[itemize,4]{label=\textbullet}
\setlist[itemize,5]{label=\textbullet}
\setlist[itemize,6]{label=\textbullet}`
\setlist[itemize,7]{label=\textbullet}
\setlist[itemize,8]{label=\textbullet}
\setlist[itemize,9]{label=\textbullet}
\renewlist{itemize}{itemize}{9}
"""

    # Write markdown and header to temp files for pandoc
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp_input:
        tmp_input.write(markdown_content)
        tmp_input_path: str = tmp_input.name

    with tempfile.NamedTemporaryFile(mode="w", suffix=".tex", delete=False) as tmp_header:
        tmp_header.write(latex_header)
        tmp_header_path: str = tmp_header.name

    try:
        # Use pandoc via subprocess for PDF conversion
        cmd: list[str] = [
            "pandoc",
            tmp_input_path,
            "-o",
            str(output_path),
            f"--pdf-engine={available_engine}",
            f"-H",
            tmp_header_path,
        ]
        result: subprocess.CompletedProcess[str] = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"pandoc failed: {result.stderr}")
    finally:
        Path(tmp_input_path).unlink(missing_ok=True)
        Path(tmp_header_path).unlink(missing_ok=True)


def main() -> int:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Convert Roam Research Markdown to standard Markdown or PDF"
    )
    parser.add_argument("input_file", type=Path, help="Path to input Markdown file")
    parser.add_argument("-o", "--output", type=Path, help="Output file path (default: input_converted.md or .pdf)")
    parser.add_argument(
        "-f",
        "--format",
        type=str,
        choices=["md", "pdf"],
        default="md",
        help="Output format: md (Markdown) or pdf (default: md)",
    )
    args: argparse.Namespace = parser.parse_args()

    input_path: Path = args.input_file
    if not input_path.exists():
        print(f"Error: {input_path} does not exist")
        return 1

    output_format: OutputFormat = args.format
    output_path: Path | None = args.output

    if output_path is None:
        extension: str = ".pdf" if output_format == "pdf" else ".md"
        output_path = input_path.with_stem(f"{input_path.stem}_converted").with_suffix(extension)

    converted: str = convert_roam_markdown(input_path)

    if output_format == "pdf":
        markdown_to_pdf(converted, output_path)
    else:
        output_path.write_text(converted)

    print(f"Converted: {input_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
