#!/bin/bash

# Jetson Nano System Setup Script
# Alternative setup for when conda packages are not available

echo "🤖 Jetson Nano System Package Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Update package lists
echo "📦 Updating package lists..."
sudo apt-get update

# Install Python 3 and pip
echo "🐍 Installing Python 3 and pip..."
sudo apt-get install -y python3 python3-pip python3-dev

# Install OpenCV and dependencies via apt (better for Jetson)
echo "👁️  Installing OpenCV via apt packages..."
sudo apt-get install -y python3-opencv python3-numpy

# Install cmake and build tools
echo "🔨 Installing build tools..."
sudo apt-get install -y cmake build-essential

# Install additional Python packages via pip
echo "📚 Installing additional Python packages..."
pip3 install --user numpy>=1.19

# Verify installation
echo "✅ Verifying installation..."
python3 -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"
python3 -c "import numpy; print(f'NumPy version: {numpy.__version__}')"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Jetson Nano system setup completed!"
echo ""
echo "📋 Next steps:"
echo "   1. Build the camera system:"
echo "      ./build.sh"
echo ""
echo "   2. Start camera streaming:"
echo "      ./run_ascamera.sh"
echo ""
echo "   3. In another terminal, run Python client:"
echo "      python3 python_live_client.py"
echo ""
echo "🎯 Your Jetson Nano is ready for Angstrong camera streaming!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
