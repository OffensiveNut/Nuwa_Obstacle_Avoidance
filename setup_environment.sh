#!/bin/bash

# Nuwa Camera Streaming Environment Setup Script
# This script creates and configures the conda environment for Angstrong camera streaming

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_NAME="nuwa_camera_streaming"

# Detect architecture and choose appropriate environment file
ARCH=$(uname -m)
echo "🔍 Detected architecture: $ARCH"

if [[ "$ARCH" == "aarch64" ]] || [[ "$ARCH" == "arm64" ]]; then
    # Jetson Nano or other ARM64 devices
    ENV_FILE="$SCRIPT_DIR/environment_jetson.yml"
    echo "🤖 Using Jetson-optimized environment file"
else
    # x86_64 and other architectures
    ENV_FILE="$SCRIPT_DIR/environment.yml"
    echo "💻 Using standard environment file"
fi

echo "🚀 Setting up Nuwa Camera Streaming Environment..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Error: conda is not installed or not in PATH"
    echo "   Please install Miniconda or Anaconda first"
    exit 1
fi

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: Environment file not found at $ENV_FILE"
    echo "   Available files:"
    ls -la "$SCRIPT_DIR"/*.yml 2>/dev/null || echo "   No .yml files found"
    exit 1
fi

# Check if environment already exists
if conda env list | grep -q "^$ENV_NAME "; then
    echo "⚠️  Environment '$ENV_NAME' already exists"
    read -p "   Do you want to remove and recreate it? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing existing environment..."
        conda env remove -n "$ENV_NAME" -y
    else
        echo "✅ Keeping existing environment. You can activate it with:"
        echo "   conda activate $ENV_NAME"
        exit 0
    fi
fi

# Create the environment
echo "📦 Creating conda environment from $ENV_FILE..."
if conda env create -f "$ENV_FILE"; then
    echo "✅ Conda environment created successfully"
else
    echo "❌ Failed to create conda environment"
    echo ""
    echo "🔧 Troubleshooting for Jetson Nano:"
    if [[ "$ARCH" == "aarch64" ]] || [[ "$ARCH" == "arm64" ]]; then
        echo "   For Jetson Nano, you might need to install OpenCV manually:"
        echo "   1. conda activate $ENV_NAME"
        echo "   2. pip install opencv-python opencv-contrib-python"
        echo "   3. Or use apt-get: sudo apt-get install python3-opencv"
        echo ""
        echo "   Alternative: Use system Python with pip:"
        echo "   pip3 install numpy opencv-python opencv-contrib-python"
    fi
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Environment setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Activate the environment:"
echo "      conda activate $ENV_NAME"
echo ""
echo "   2. Build the camera system:"
echo "      ./build.sh"
echo ""
echo "   3. Start camera streaming:"
echo "      ./run_ascamera.sh"
echo ""
echo "   4. In another terminal, run Python client:"
echo "      conda activate $ENV_NAME"
echo "      python3 python_live_client.py"
echo ""
echo "📖 For complete documentation, see README.md"
echo ""
echo "🎯 Your environment is ready for Angstrong camera streaming and"
echo "   3-Zone Danger Detection + TTC obstacle avoidance development!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
