#!/bin/bash

# Get App Name from config.py (simple parsing)
APP_NAME=$(python -c "import config; print(config.APP_NAME)")
if [ -z "$APP_NAME" ]; then
    APP_NAME="ACR" # Fallback
    echo "Warning: Could not determine APP_NAME from config.py, using fallback: $APP_NAME"
fi

ICON_FILE="assets/icons/default_icon.png" # PyInstaller can sometimes use .png for Linux/macOS
# For macOS, an .icns file is preferred: --icon="assets/icons/default_icon.icns"
# For Windows, an .ico file is preferred: --icon="assets/icons/default_icon.ico"

echo "Starting PyInstaller build for $APP_NAME..."
echo "Output will be in dist/$APP_NAME"

# Clean previous builds
rm -rf build/
rm -rf dist/
rm -f "$APP_NAME.spec"

# PyInstaller command
# --noconfirm: Overwrite output directory without asking
# --log-level WARN: Reduce verbosity, can be DEBUG for troubleshooting
# --add-data: Format is "SOURCE:DESTINATION_IN_BUNDLE"
#             On macOS/Linux, use ':' as separator. On Windows, use ';'
#             The destination '.' means the root of the bundle.
#             'assets:assets' will copy the 'assets' folder into the bundle's 'assets' folder.
# --hidden-import: Sometimes needed for libraries that PyInstaller doesn't auto-detect.
#                  Examples: 'pystray.backend.xorg', 'sounddevice._cffi'
#                  These are often platform and library specific.
#                  For now, we'll omit them and add if build/run fails.
# --windowed: Use for GUI applications to not show a console window (especially on Windows).
#             On macOS, this creates an app bundle.
# --onefile: Creates a single executable file.

# Common hidden imports that might be needed for the libraries we're using:
# For pystray: backend might need to be specified depending on the OS.
# For keyboard: might need 'Xlib' on Linux if not automatically found.
# For sounddevice: '_cffi' part is often needed.

# Let's try a basic command first and add hidden imports if testing reveals issues.
# A more robust script might detect OS and add specific hidden imports.

# Note on paths: PyInstaller runs from the script's directory.
# Ensure assets paths are correct relative to the project root where build.sh is.

pyinstaller --name "$APP_NAME" \
    --onefile \
    --windowed \
    --icon="$ICON_FILE" \
    --add-data "assets:assets" \
    --noconfirm \
    --log-level INFO \
    main.py

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "Build successful!"
    echo "Executable created in dist/"
    ls -l dist/
else
    echo "Build failed. See output above for details."
    exit 1
fi

echo "Build script finished."
