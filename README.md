# Nuwa Obstacle Avoidance - Camera Streaming System

A complete real-time streaming solution for Angstrong EAI Camera with enhanced depth visualization, designed for 3-Zone Danger Detection and Time-to-Collision (TTC) obstacle avoidance algorithms.

## 📋 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [🎯 Features](#-features)
- [🔧 System Requirements](#-system-requirements)
- [📦 Environment Setup](#-environment-setup)
- [🎮 Usage](#-usage)
- [🎨 Depth Visualization](#-depth-visualization)
- [🛠️ Development](#-development)
- [📁 Project Structure](#-project-structure)
- [🔍 Troubleshooting](#-troubleshooting)

## 🚀 Quick Start

### Automated Setup (Recommended)
```bash
# Navigate to project directory
cd /path/to/EaiCameraSdk_v1.2.28.20241015/demo/linux_ros/linux

# One-command setup
./setup_environment.sh

# Activate environment
conda activate nuwa_camera_streaming

# Build and run
./build.sh
./run_ascamera.sh

# In another terminal, run Python client
conda activate nuwa_camera_streaming
python3 python_live_client.py
```

## 🎯 Features

### Core Capabilities
- ✅ **Real-time Camera Streaming**: 13+ FPS depth + RGB data
- ✅ **TCP Socket Communication**: Robust multi-client support  
- ✅ **Enhanced Depth Visualization**: Optimized for obstacle detection
- ✅ **Python OpenCV Integration**: Direct access to camera data
- ✅ **BGR Color Compatibility**: No conversion needed
- ✅ **Robust Error Handling**: Graceful client disconnection handling

### Specialized Tools
- **Live Streaming Client**: Real-time depth + RGB visualization
- **Depth Comparison Tool**: Side-by-side old vs improved visualization
- **Color Format Tester**: RGB format validation and testing
- **Environment Setup**: Automated conda environment configuration

## 🔧 System Requirements

- **OS**: Linux x86_64 (tested on Ubuntu/similar)
- **Hardware**: USB 3.0 port for camera connection
- **Software**: Conda/Miniconda installed
- **Permissions**: USB device access (handled by setup script)
- **Camera**: Angstrong EAI HP60C (640x480 depth + RGB)

## 📦 Environment Setup

### Option 1: Automated Setup (Recommended)
```bash
./setup_environment.sh
```
*Automatically detects your architecture and uses the appropriate environment file.*

### Option 2: Jetson Nano / ARM64 System Setup
If conda fails on Jetson Nano (common issue), use system packages instead:
```bash
./setup_jetson_system.sh
```
*This uses apt packages which are more reliable on Jetson Nano Ubuntu 18.04.*

### Option 3: Manual Conda Setup
```bash
# For x86_64 systems
conda env create -f environment.yml

# For ARM64/Jetson systems
conda env create -f environment_jetson.yml

conda activate nuwa_camera_streaming
```

### Option 4: pip-only Installation (Limited compatibility)
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Details
- **Environment Name**: `nuwa_camera_streaming`
- **Python Version**: 3.8+
- **Key Packages**:
  - OpenCV 4.2.0+ (Computer Vision)
  - NumPy 1.19+ (Numerical computing)
  - CMake 3.16+ (Build system)

### Jetson Nano Specific Notes
- **Architecture**: ARM64/aarch64 detected automatically
- **OpenCV**: Installed via apt packages for better compatibility
- **Performance**: Optimized for embedded systems
- **Alternative**: If conda fails, system packages provide reliable fallback

## 🎮 Usage

### Basic Workflow

1. **Setup Environment** (one-time):
   ```bash
   ./setup_environment.sh
   ```

2. **Activate Environment**:
   ```bash
   conda activate nuwa_camera_streaming
   ```

3. **Build Camera System**:
   ```bash
   ./build.sh
   ```

4. **Start Camera + Streaming Server**:
   ```bash
   ./run_ascamera.sh
   ```

5. **Connect Python Client** (in another terminal):
   ```bash
   conda activate nuwa_camera_streaming
   python3 python_live_client.py
   ```

### Available Python Clients

| Script | Purpose | Usage |
|--------|---------|-------|
| `python_live_client.py` | Main streaming client with enhanced depth visualization | Real-time obstacle detection |
| `depth_comparison.py` | Compare old vs improved depth coloring | Visualization development |
| `color_test_client.py` | Test RGB color format variants | Color format validation |

### Keyboard Controls
- **`q`**: Quit application
- **`s`**: Save current frame images
- **`Ctrl+C`**: Emergency stop

## 🎨 Depth Visualization

### Enhanced Color Mapping
Our improved depth visualization provides intuitive obstacle detection:

- **🔴 Red**: Closer objects (immediate danger zone)
- **🟡 Yellow/Green**: Medium distance objects  
- **🔵 Blue**: Farther objects (safe zone)
- **🔵 Deep Blue/Black**: Out-of-range or invalid depth areas

### Technical Implementation
```python
# Define valid depth range (adjustable based on camera specs)
valid_mask = (depth_img > 100) & (depth_img < 60000)  # ~0.1m to 6m range

# Process only valid depth values for better contrast
valid_depth = depth_img[valid_mask]
min_valid = np.min(valid_depth)
max_valid = np.max(valid_depth)

# Normalize and invert (closer = red, farther = blue)
depth_processed = (depth_img - min_valid) / (max_valid - min_valid)
depth_inverted = 255 - (depth_processed * 255)
depth_colored = cv2.applyColorMap(depth_inverted, cv2.COLORMAP_JET)

# Set invalid areas to deep blue
depth_colored[~valid_mask] = [30, 0, 0]  # BGR format
```

### Adjustable Parameters
```python
MIN_VALID_DEPTH = 100      # ~0.1m minimum detection
MAX_VALID_DEPTH = 60000    # ~6m maximum detection  
INVALID_COLOR = [30, 0, 0] # Deep blue for out-of-range areas
```

### Benefits for Obstacle Avoidance
1. **Clear Danger Zones**: Red areas indicate immediate obstacles requiring avoidance
2. **Invalid Area Handling**: Deep blue clearly shows areas without valid depth data
3. **Better Contrast**: Only valid depth range is normalized, improving detail in useful areas
4. **3-Zone Detection Ready**: Perfect for implementing danger zones:
   - **Red Zone**: Immediate danger (stop/reverse)
   - **Yellow Zone**: Caution (reduce speed)  
   - **Blue Zone**: Safe (normal speed)

## 🛠️ Development

### Project Architecture
```
Camera SDK (C++) ←→ TCP Stream Server ←→ Python Clients
     ↓                      ↓                    ↓
HP60C Camera          Port 8888         OpenCV Display
```

### Key Components

#### C++ Streaming Server
- **`PythonStreamServer.cpp/h`**: TCP streaming implementation
- **`Demo.cpp`**: Modified camera demo with streaming integration
- **`CMakeLists.txt`**: Build configuration with streaming support

#### Python Clients
- **`python_live_client.py`**: Main client with enhanced visualization
- **Threading**: Separate receive and display threads for optimal performance
- **Error Handling**: Robust socket communication with reconnection support

### API Access
```python
# Get latest frames for algorithm processing
depth_img, rgb_img, ir_img = client.get_latest_frames()

# Process depth data for obstacle detection
valid_mask = (depth_img > 100) & (depth_img < 60000)
closest_distance = np.min(depth_img[valid_mask]) if np.any(valid_mask) else float('inf')
```

## 📁 Project Structure

```
├── README.md                 # This comprehensive documentation
├── environment.yml           # Conda environment specification
├── requirements.txt          # Basic pip requirements
├── setup_environment.sh      # Automated environment setup
├── .gitignore               # Git ignore patterns
│
├── build.sh                 # Build script
├── run_ascamera.sh          # Camera startup script
├── CMakeLists.txt           # Build configuration
│
├── include/
│   ├── PythonStreamServer.h # TCP streaming server header
│   └── ...                  # Other camera SDK headers
│
├── src/
│   ├── PythonStreamServer.cpp # TCP streaming implementation
│   ├── Demo.cpp             # Modified camera demo
│   └── ...                  # Other camera SDK sources
│
├── python_live_client.py    # Main Python streaming client
├── depth_comparison.py      # Depth visualization comparison
├── color_test_client.py     # RGB color format tester
│
├── configurationfiles/      # Camera configuration files
├── libs/                    # SDK libraries
└── build/                   # Build output directory
```

## 🔍 Troubleshooting

### Common Issues

**Camera Not Detected**
```bash
# Check USB connection and permissions
lsusb
sudo usermod -a -G plugdev $USER
# Reboot after adding to group
```

**Build Failures**
```bash
# Clean and rebuild
rm -rf build/
./build.sh
```

**Python Client Connection Issues**
```bash
# Ensure camera server is running first
./run_ascamera.sh

# In another terminal
python3 python_live_client.py
```

**Environment Issues**
```bash
# Reset environment
conda env remove -n nuwa_camera_streaming
./setup_environment.sh
```

**Jetson Nano Specific Issues**

*Problem*: `PackagesNotFoundError` with opencv or other packages
```bash
# Solution 1: Use Jetson system setup instead
./setup_jetson_system.sh

# Solution 2: Manual system package installation
sudo apt-get update
sudo apt-get install python3-opencv python3-numpy cmake
```

*Problem*: Architecture detection or ARM64 compatibility
```bash
# Check architecture
uname -m
# Should show: aarch64

# Use Jetson-specific environment
conda env create -f environment_jetson.yml
```

*Problem*: Conda installation fails completely
```bash
# Use system Python instead (recommended for Jetson)
sudo apt-get install python3 python3-pip python3-opencv
pip3 install --user numpy

# Then proceed with build
./build.sh
python3 python_live_client.py  # No conda activation needed
```

### Performance Optimization
- **Frame Rate**: Typically 13+ FPS (sufficient for real-time obstacle avoidance)
- **Latency**: < 100ms end-to-end (camera to Python display)
- **Memory**: ~50MB for streaming server + clients

### Development Tips
- Use `depth_comparison.py` to test visualization improvements
- Monitor camera server logs for connection debugging
- Adjust depth range parameters based on your environment
- Save frames using `s` key for algorithm development

---

## 🎯 Ready for Algorithm Development

Your complete streaming infrastructure is now ready for implementing:
- **3-Zone Danger Detection**: Using enhanced depth visualization
- **Time-to-Collision (TTC) algorithms**: Real-time distance analysis
- **Obstacle avoidance**: Multi-threaded processing pipeline
- **Path planning systems**: Direct access to depth + RGB data

**Perfect foundation for your Nuwa obstacle avoidance project!** 🚀✨
