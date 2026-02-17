#!/bin/bash
# Script to refresh .mdbundle folders so macOS recognizes them properly
# Run this on existing .mdbundle folders created before setting up the handler

echo "Refreshing .mdbundle folders..."
echo ""

# Check if a directory was provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <directory>"
    echo ""
    echo "This will refresh all .mdbundle folders in the specified directory"
    echo "so macOS recognizes them with the correct type."
    echo ""
    echo "Example:"
    echo "  $0 ~/wip"
    echo "  $0 ."
    exit 1
fi

SEARCH_DIR="$1"

# Check if directory exists
if [ ! -d "$SEARCH_DIR" ]; then
    echo "Error: Directory not found: $SEARCH_DIR"
    exit 1
fi

# Find all .mdbundle folders
BUNDLES=$(find "$SEARCH_DIR" -maxdepth 1 -name "*.mdbundle" -type d)

if [ -z "$BUNDLES" ]; then
    echo "No .mdbundle folders found in $SEARCH_DIR"
    exit 0
fi

COUNT=0
while IFS= read -r bundle; do
    if [ -d "$bundle" ]; then
        echo "Refreshing: $bundle"
        # Touch the folder to update modification time
        touch "$bundle"
        # Force mdimport to reindex
        mdimport "$bundle" 2>/dev/null
        COUNT=$((COUNT + 1))
    fi
done <<< "$BUNDLES"

echo ""
echo "✓ Refreshed $COUNT .mdbundle folder(s)"
echo ""
echo "You can now right-click on these folders in Finder and see OpenMDBundle"
echo "in the 'Open with:' menu."
