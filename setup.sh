#!/bin/bash

echo "--- ASDGPT Setup Script ---"

# Create directories
echo "Creating data directories..."
mkdir -p user_data
mkdir -p captures/erotic
mkdir -p drafts/instagram
mkdir -p assets

# Check dependencies
echo "Checking system dependencies..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! command -v xprop &> /dev/null; then
        echo "Warning: 'xprop' not found. Window detection may fail. Install 'x11-utils'."
    fi
    if ! command -v espeak &> /dev/null; then
        echo "Warning: 'espeak' not found. System TTS may fail. Install 'espeak'."
    fi
    if ! command -v ffmpeg &> /dev/null; then
        echo "Warning: 'ffmpeg' not found. Audio processing may fail. Install 'ffmpeg'."
    fi
fi

# Python deps
echo "Installing Python dependencies..."
if command -v pip &> /dev/null; then
    pip install -r requirements.txt
else
    echo "Error: 'pip' not found. Please activate your virtual environment."
fi

echo "--- Setup Complete ---"
echo "Run 'python tools/config_gui.py' to configure the application."
echo "Run 'python main.py' to start."
