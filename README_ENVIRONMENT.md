# Nuwa Camera Streaming Environment

This directory contains all the necessary configuration files to reproduce the conda environment used for Angstrong EAI Camera streaming and Python integration.

## 🚀 Quick Setup

### Option 1: Automated Setup (Recommended)
```bash
# Make sure you're in the project directory
cd /path/to/EaiCameraSdk_v1.2.28.20241015/demo/linux_ros/linux

# Run the setup script
./setup_environment.sh
```

### Option 2: Manual Setup
```bash
# Create conda environment from YAML file
conda env create -f environment.yml

# Activate the environment
conda activate nuwa_camera_streaming
```

### Option 3: pip-only Installation (Limited compatibility)
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

## 📋 Environment Details

- **Environment Name**: `nuwa_camera_streaming`
- **Python Version**: 3.8.15
- **Key Packages**:
  - OpenCV 4.2.0 (Computer Vision)
  - NumPy 1.24.4 (Numerical computing)
  - CMake 3.18.4 (Build system)

## 🎯 Usage Workflow

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

4. **Start Camera Streaming**:
   ```bash
   ./run_ascamera.sh
   ```

5. **Run Python Client** (in another terminal):
   ```bash
   conda activate nuwa_camera_streaming
   python3 python_live_client.py
   ```

## 📁 Configuration Files

- `environment.yml` - Complete conda environment specification
- `requirements.txt` - Basic pip requirements (limited compatibility)
- `setup_environment.sh` - Automated setup script
- `.gitignore` - Git ignore patterns for development

## 🔧 Development Notes

- This environment is optimized for Angstrong EAI Camera SDK v1.2.28
- Compatible with HP60C camera model (640x480 depth + RGB)
- Configured for real-time streaming at ~13+ FPS
- Ready for 3-Zone Danger Detection + TTC obstacle avoidance algorithms

## 🌟 Features

- ✅ Real-time camera streaming
- ✅ TCP socket communication 
- ✅ Python OpenCV integration
- ✅ Robust error handling
- ✅ Multi-client support
- ✅ BGR color format compatibility

## 🚧 System Requirements

- Linux x86_64 (tested on Ubuntu/similar)
- USB 3.0 port for camera connection
- Conda/Miniconda installed
- Sufficient permissions for USB device access

---

**Ready for implementing your obstacle avoidance algorithms!** 🎯
