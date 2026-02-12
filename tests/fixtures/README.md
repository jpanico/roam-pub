# Test Fixtures

This directory contains test data used by the mdplay test suite.

## Directory Structure

- `markdown/` - Sample Roam Research Markdown files (`.gfm` and `.md` files)
- `images/` - Test images fetched from Roam Research

## Files

### Markdown Files
- `Test Article.gfm` - Simple test article with one Firebase image link
- `Test Article_converted.md` - Converted version with local image reference
- `[[Illustration]] Mood Boards.gfm` - Complex article with multiple images
- `Illustrator Brief.md` - Additional test markdown file

### Images
- `flower.jpeg` - Test image used in `test_live` test case

## Usage

Test files reference fixtures using relative paths from the project root:
```python
with open("tests/fixtures/images/flower.jpeg", "rb") as f:
    expected_contents = f.read()
```
