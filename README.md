# roam-pub

Markdown utilities for working with Roam Research exports.

## Development Setup

### Prerequisites

- Python 3.14 or higher
- Git

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/roam-pub.git
   cd roam-pub
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install the package in editable mode with development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

   This installs:
   - The `roam-pub` package in editable mode (changes to code are immediately reflected)
   - Runtime dependencies: `pydantic`, `requests`
   - Development dependencies: `pytest`, `black`

### Running Tests

Once the development environment is set up, you can run tests using pytest:

```bash
pytest
```

To run tests with verbose output:
```bash
pytest -v
```

To run a specific test file:
```bash
pytest tests/test_roam_asset.py
```

### Code Formatting

This project uses Black for code formatting:

```bash
black .
```

To check formatting without making changes:
```bash
black --check .
```

## Project Structure

```
roam-pub/
├── src/
│   └── roam_pub/          # Main package code
│       ├── __init__.py
│       ├── roam_asset.py
│       ├── roam_md_bundle.py
│       └── bundle_roam_md.py
├── tests/                  # Test files
│   ├── test_roam_asset.py
│   └── test_roam_md_bundle.py
├── bundle-roam-md.sh       # Shell wrapper for direct execution
├── pyproject.toml          # Project configuration
└── README.md
```

## Usage

### Running the Bundle Script

The package provides the `bundle-roam-md` command-line utility for bundling Roam Research markdown files with their Firebase-hosted images.

**Method 1: Using the installed command (recommended)**

After installing the package with `pip install -e ".[dev]"`, you can use the installed command with named arguments:

```bash
bundle-roam-md --markdown-file <file> --port <port> --graph <name> --token <token> --output <dir>
```

Example with long flags:
```bash
bundle-roam-md --markdown-file my_notes.md --port 3333 --graph SCFH --token your-bearer-token --output ./output
```

Example with short flags:
```bash
bundle-roam-md -m my_notes.md -p 3333 -g SCFH -t your-bearer-token -o ./output
```

**Method 2: Using the shell wrapper script**

For direct execution without activating the virtual environment:

```bash
./bundle-roam-md.sh --markdown-file <file> --port <port> --graph <name> --token <token> --output <dir>
```

Example:
```bash
./bundle-roam-md.sh -m my_notes.md -p 3333 -g SCFH -t your-bearer-token -o ./output
```

**Getting help:**

```bash
bundle-roam-md --help
# or
./bundle-roam-md.sh --help
```

### What it does

The script:
1. Reads a Roam Research markdown file
2. Finds all Firebase-hosted images (firebasestorage.googleapis.com URLs)
3. Fetches each image via the Roam Local API
4. Saves images locally in a `.bundle` directory
5. Updates the markdown file with local image references
6. Performs cleanup: normalizes link text and removes escaped brackets

### Output

Creates a directory named `<markdown_file>.bundle/` containing:
- Updated markdown file with local image references
- All downloaded images

## License

TBD
