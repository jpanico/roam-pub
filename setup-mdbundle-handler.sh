#!/bin/bash
# Setup script to create .mdbundle handler for macOS using AppleScript droplet

set -e

APP_NAME="OpenMDBundle"
APP_PATH="$HOME/Applications/${APP_NAME}.app"

echo "Creating ${APP_NAME}.app as AppleScript droplet..."

# Create temporary AppleScript source
cat > /tmp/open-mdbundle-droplet.applescript << 'APPLESCRIPT'
on run
    display alert "OpenMDBundle" message "Please double-click a .mdbundle folder in Finder, or drag one onto this application icon."
end run

on open theFiles
    repeat with aFile in theFiles
        set bundlePath to POSIX path of aFile
        set bundleName to do shell script "basename " & quoted form of bundlePath

        -- Remove .mdbundle extension to get the .md filename
        if bundleName ends with ".mdbundle" then
            set mdFileName to text 1 thru -10 of bundleName & ".md"
        else
            set mdFileName to bundleName & ".md"
        end if

        set mdFilePath to bundlePath & "/" & mdFileName

        -- Check if the markdown file exists
        try
            do shell script "test -f " & quoted form of mdFilePath

            -- Open in Typora
            try
                do shell script "open -a Typora " & quoted form of mdFilePath
            on error errMsg
                display alert "Error Opening Typora" message "Could not open Typora. Make sure it is installed in /Applications/." & return & return & "Error: " & errMsg
            end try
        on error
            display alert "Markdown File Not Found" message "Expected to find: " & mdFileName & " in the bundle." & return & return & "Bundle: " & bundlePath
        end try
    end repeat
end open
APPLESCRIPT

# Compile as droplet application
osacompile -x -o "${APP_PATH}" /tmp/open-mdbundle-droplet.applescript

# Clean up temp file
rm /tmp/open-mdbundle-droplet.applescript

echo "✓ Created ${APP_PATH}"

# Update the Info.plist with bundle identifier and custom types
echo "Updating Info.plist..."

# Add bundle identifier if missing
plutil -insert CFBundleIdentifier -string "com.local.openmdbundle" "${APP_PATH}/Contents/Info.plist" 2>/dev/null || true

# Replace document types to use our UTI
plutil -replace CFBundleDocumentTypes -xml '
<array>
    <dict>
        <key>CFBundleTypeName</key>
        <string>Markdown Bundle</string>
        <key>CFBundleTypeRole</key>
        <string>Viewer</string>
        <key>LSHandlerRank</key>
        <string>Owner</string>
        <key>LSItemContentTypes</key>
        <array>
            <string>com.local.markdown-bundle</string>
        </array>
    </dict>
</array>' "${APP_PATH}/Contents/Info.plist"

# Add UTI declaration if missing
plutil -insert UTExportedTypeDeclarations -xml '
<array>
    <dict>
        <key>UTTypeIdentifier</key>
        <string>com.local.markdown-bundle</string>
        <key>UTTypeDescription</key>
        <string>Markdown Bundle</string>
        <key>UTTypeConformsTo</key>
        <array>
            <string>com.apple.package</string>
            <string>public.directory</string>
        </array>
        <key>UTTypeTagSpecification</key>
        <dict>
            <key>public.filename-extension</key>
            <array>
                <string>mdbundle</string>
            </array>
        </dict>
    </dict>
</array>' "${APP_PATH}/Contents/Info.plist" 2>/dev/null || true

echo "✓ Updated Info.plist"

# Register with Launch Services
echo "Registering with Launch Services..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "${APP_PATH}"

echo "✓ Registered ${APP_NAME}.app"

# Touch the app to update its modification time
touch "${APP_PATH}"

echo "Refreshing Launch Services..."
killall Finder 2>/dev/null || true

echo "✓ Launch Services refreshed"

# Set as default handler using duti if available
if command -v duti &> /dev/null; then
    echo "Setting as default handler for .mdbundle..."
    duti -s com.local.openmdbundle com.local.markdown-bundle all
    echo "✓ Set as default handler"
else
    echo "Note: 'duti' not found. You'll need to manually set the default app."
fi

echo ""
echo "Setup complete!"
echo ""

if command -v duti &> /dev/null; then
    echo "✓ .mdbundle folders will now automatically open with ${APP_NAME}"
    echo ""
    echo "To test: Double-click any .mdbundle folder in Finder"
else
    echo "Manual setup required:"
    echo "1. Find any .mdbundle folder in Finder"
    echo "2. Right-click > Get Info (⌘I)"
    echo "3. Under 'Open with:', select '${APP_NAME}'"
    echo "4. Click 'Change All...' to apply to all .mdbundle folders"
fi

echo ""
echo "Note: If double-clicking doesn't work immediately:"
echo "  1. Log out and log back in"
echo "  2. Or try: open ~/path/to/your.mdbundle"
