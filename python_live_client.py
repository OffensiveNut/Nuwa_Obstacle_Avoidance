#!/usr/bin/env python3
"""
Python Live Stream Client for Angstrong Camera
Connects to C++ stream server for real-time camera data
"""

import socket
import struct
import numpy as np
import cv2
import time
import threading
import os
from typing import Optional, Tuple, List
from collections import deque

# TTS and Audio imports
try:
    from gtts import gTTS
    import pygame
    from pydub import AudioSegment
    TTS_AVAILABLE = True
except ImportError as e:
    print(f"TTS packages not available: {e}")
    print("Install with: pip install gtts pygame pydub")
    TTS_AVAILABLE = False

class TTCCalculator:
    """Time-to-Collision calculator for tracking object approach velocity"""
    
    def __init__(self, history_size: int = 10, min_velocity_threshold: float = 0.01):
        """
        Initialize TTC calculator
        
        Args:
            history_size: Number of distance measurements to keep for velocity calculation
            min_velocity_threshold: Minimum velocity (m/s) to consider for TTC calculation
        """
        self.history_size = history_size
        self.min_velocity_threshold = min_velocity_threshold
        
        # Store distance history for each zone: [left, center, right]
        self.distance_history = [deque(maxlen=history_size) for _ in range(3)]
        self.time_history = [deque(maxlen=history_size) for _ in range(3)]
        
    def update_and_calculate_ttc(self, distances: List[float]) -> List[Optional[float]]:
        """
        Update distance history and calculate TTC for each zone
        
        Args:
            distances: List of [left_dist, center_dist, right_dist] in meters
            
        Returns:
            List of TTC values in seconds [left_ttc, center_ttc, right_ttc]
            None if TTC cannot be calculated (no approach velocity)
        """
        current_time = time.time()
        ttc_values = []
        
        for zone_idx, distance in enumerate(distances):
            # Add current measurement
            self.distance_history[zone_idx].append(distance)
            self.time_history[zone_idx].append(current_time)
            
            # Calculate TTC if we have enough history
            if len(self.distance_history[zone_idx]) >= 3:
                ttc = self._calculate_zone_ttc(zone_idx)
                ttc_values.append(ttc)
            else:
                ttc_values.append(None)  # Not enough data yet
                
        return ttc_values
    
    def _calculate_zone_ttc(self, zone_idx: int) -> Optional[float]:
        """Calculate TTC for a specific zone using linear regression on recent data"""
        distances = list(self.distance_history[zone_idx])
        times = list(self.time_history[zone_idx])
        
        if len(distances) < 3:
            return None
            
        # Use linear regression to estimate velocity (distance change over time)
        # Convert to numpy arrays for calculation
        time_diff = np.array(times) - times[0]  # Relative time
        dist_array = np.array(distances)
        
        # Calculate velocity using simple linear regression
        if len(time_diff) > 1 and time_diff[-1] > time_diff[0]:
            # Velocity = slope of distance vs time (negative means approaching)
            velocity = (dist_array[-1] - dist_array[0]) / (time_diff[-1] - time_diff[0])
            
            # Only calculate TTC for approaching objects (negative velocity)
            if velocity < -self.min_velocity_threshold:
                current_distance = distances[-1]
                ttc = current_distance / abs(velocity)  # Time to reach distance = 0
                
                # Clamp TTC to reasonable range (0.1 to 60 seconds)
                if 0.1 <= ttc <= 60.0:
                    return ttc
                    
        return None  # No collision risk or unreliable data

class TTSAudioManager:
    """Text-to-Speech Audio Manager for TTC warnings"""
    
    def __init__(self, audio_dir: str = "audio_cache"):
        """
        Initialize TTS Audio Manager
        
        Args:
            audio_dir: Directory to store cached audio files
        """
        self.audio_dir = audio_dir
        self.audio_files = {}
        self.last_warning_time = {}
        self.warning_cooldown = 2.0  # Minimum seconds between same warning
        
        # Create audio directory
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # Initialize pygame mixer if available
        if TTS_AVAILABLE:
            try:
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                self.audio_enabled = True
                print("Audio system initialized")
            except Exception as e:
                print(f"Failed to initialize audio: {e}")
                self.audio_enabled = False
        else:
            self.audio_enabled = False
            
        # Pre-generate Indonesian warning audio files
        self._generate_warning_audio()
    
    def _generate_warning_audio(self):
        """Generate and cache Indonesian TTS audio files"""
        if not self.audio_enabled:
            return
            
        warnings = {
            "kanan": "Kanan!",      # Right!
            "kiri": "Kiri!",        # Left!
            "tengah": "Tengah!"     # Center!
        }
        
        for key, text in warnings.items():
            mp3_file = os.path.join(self.audio_dir, f"{key}.mp3")
            
            # Generate if doesn't exist
            if not os.path.exists(mp3_file):
                try:
                    print(f"Generating TTS audio for: {text}")
                    
                    # Generate TTS with Indonesian language and save directly as MP3
                    tts = gTTS(text=text, lang='id', slow=False)
                    tts.save(mp3_file)
                    
                    print(f"Generated: {mp3_file}")
                    
                except Exception as e:
                    print(f"Failed to generate audio for {key}: {e}")
                    continue
            
            # Store file path
            if os.path.exists(mp3_file):
                self.audio_files[key] = mp3_file
    
    def play_warning_sequence(self, zones_under_threshold: List[str]):
        """
        Play sequential audio warnings for zones with TTC under threshold
        
        Args:
            zones_under_threshold: List of zone names ["kanan", "kiri", "tengah"]
                                 in order of priority (right -> left -> center)
        """
        if not self.audio_enabled or not zones_under_threshold:
            return
            
        current_time = time.time()
        
        # Check cooldown for this specific combination
        warning_key = "_".join(sorted(zones_under_threshold))
        
        if (warning_key in self.last_warning_time and 
            current_time - self.last_warning_time[warning_key] < self.warning_cooldown):
            return  # Still in cooldown
        
        # Update last warning time
        self.last_warning_time[warning_key] = current_time
        
        # Play warnings sequentially in a separate thread to avoid blocking
        thread = threading.Thread(target=self._play_sequence_thread, args=(zones_under_threshold,))
        thread.daemon = True
        thread.start()
    
    def _play_sequence_thread(self, zones: List[str]):
        """Play audio sequence in separate thread"""
        try:
            for i, zone in enumerate(zones):
                if zone in self.audio_files:
                    # Load and play the audio file
                    pygame.mixer.music.load(self.audio_files[zone])
                    pygame.mixer.music.play()
                    
                    # Wait for audio to finish before playing next
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    
                    # Small gap between warnings
                    if i < len(zones) - 1:
                        time.sleep(0.2)
                        
        except Exception as e:
            print(f"Error playing audio sequence: {e}")

# Global TTC calculator and audio manager instances
ttc_calculator = TTCCalculator()
audio_manager = TTSAudioManager() if TTS_AVAILABLE else None

def analyze_danger_zones(depth_img: np.ndarray) -> Tuple[Tuple[str, float, Optional[float]], Tuple[str, float, Optional[float]], Tuple[str, float, Optional[float]]]:
    """
    Analyze depth image for 3-zone danger detection with Time-to-Collision calculation
    
    Args:
        depth_img: 16-bit depth image
        
    Returns:
        Tuple of ((left_status, left_min_dist, left_ttc), (center_status, center_min_dist, center_ttc), (right_status, right_min_dist, right_ttc))
        Each status is either "safe" or "warn", distances in meters, TTC in seconds (None if no collision risk)
    """
    if depth_img is None:
        return ("safe", 0.0, None), ("safe", 0.0, None), ("safe", 0.0, None)
    
    height, width = depth_img.shape
    
    # Define zones (30% left, 40% center, 30% right)
    left_end = int(width * 0.3)
    center_end = int(width * 0.7)
    
    left_zone = depth_img[:, :left_end]
    center_zone = depth_img[:, left_end:center_end]
    right_zone = depth_img[:, center_end:]
    
    # Define danger thresholds (in depth units, assuming ~1mm per unit)
    CENTER_THRESHOLD = 1500   # 1.5 meters for center zone
    SIDE_THRESHOLD = 1000     # 1.0 meters for left/right zones
    
    def check_zone_danger(zone: np.ndarray, threshold: int) -> Tuple[str, float]:
        """Check if any valid depth in zone is below threshold, return status and min distance"""
        # Filter valid depth values (exclude 0 and very high values)
        valid_mask = (zone > 100) & (zone < 60000)
        
        if not np.any(valid_mask):
            return "safe", 0.0  # No valid data, assume safe
        
        valid_depths = zone[valid_mask]
        min_distance = np.min(valid_depths)
        min_distance_m = min_distance / 1000.0  # Convert to meters
        
        status = "warn" if min_distance < threshold else "safe"
        return status, min_distance_m
    
    # Analyze each zone
    left_result = check_zone_danger(left_zone, SIDE_THRESHOLD)
    center_result = check_zone_danger(center_zone, CENTER_THRESHOLD)
    right_result = check_zone_danger(right_zone, SIDE_THRESHOLD)
    
    # Calculate TTC for each zone
    distances = [left_result[1], center_result[1], right_result[1]]
    ttc_values = ttc_calculator.update_and_calculate_ttc(distances)
    
    # Combine results with TTC
    left_final = (left_result[0], left_result[1], ttc_values[0])
    center_final = (center_result[0], center_result[1], ttc_values[1])
    right_final = (right_result[0], right_result[1], ttc_values[2])
    
    return left_final, center_final, right_final

class CameraStreamClient:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.connected = False
        
        # Frame data
        self.latest_depth = None
        self.latest_rgb = None
        self.latest_ir = None
        self.frame_count = 0
        self.start_time = time.time()
        
        # Threading
        self.receive_thread = None
        self.lock = threading.Lock()
        
    def connect(self) -> bool:
        """Connect to the C++ stream server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"Connected to camera stream server at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        self.running = False
        self.connected = False
        
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2)
            
        if self.socket:
            self.socket.close()
            self.socket = None
        
        print("Disconnected from camera stream server")
    
    def start_streaming(self) -> bool:
        """Start receiving stream data"""
        if not self.connected:
            return False
            
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        print("Started receiving camera stream")
        return True
    
    def _receive_loop(self):
        """Main receive loop running in separate thread"""
        while self.running and self.connected:
            try:
                # Receive frame header - FrameHeader structure size
                # uint64_t timestamp + 10 * uint32_t = 8 + 40 = 48 bytes
                header_data = self._receive_exact(48)  # 8 + 10*4 = 48 bytes
                if not header_data:
                    break
                    
                # Unpack header: 1 uint64 + 10 uint32
                header = struct.unpack('<Q10I', header_data)  # Little endian format
                timestamp = header[0]
                frame_id = header[1]
                depth_width = header[2]
                depth_height = header[3]
                depth_size = header[4]
                rgb_width = header[5]
                rgb_height = header[6]
                rgb_size = header[7]
                ir_width = header[8]
                ir_height = header[9]
                ir_size = header[10]
                
                # Receive depth data
                depth_img = None
                if depth_size > 0:
                    depth_data = self._receive_exact(depth_size)
                    if depth_data:
                        depth_array = np.frombuffer(depth_data, dtype=np.uint16)
                        depth_img = depth_array.reshape((depth_height, depth_width))
                
                # Receive RGB data
                rgb_img = None
                if rgb_size > 0:
                    rgb_data = self._receive_exact(rgb_size)
                    if rgb_data:
                        rgb_array = np.frombuffer(rgb_data, dtype=np.uint8)
                        
                        # Data is already in BGR format - use directly
                        if rgb_size == rgb_width * rgb_height * 3:  # BGR24
                            rgb_img = rgb_array.reshape((rgb_height, rgb_width, 3))
                            # No color conversion needed - data is already BGR
                        elif rgb_size == rgb_width * rgb_height * 2:  # YUV422 or similar
                            # Try YUV422 conversion
                            try:
                                yuv_img = rgb_array.reshape((rgb_height, rgb_width, 2))
                                rgb_img = cv2.cvtColor(yuv_img, cv2.COLOR_YUV2BGR_YUYV)
                            except:
                                try:
                                    yuv_img = rgb_array.reshape((rgb_height, rgb_width, 2))
                                    rgb_img = cv2.cvtColor(yuv_img, cv2.COLOR_YUV2BGR_UYVY)
                                except:
                                    print(f"Failed to convert YUV data of size {rgb_size}")
                        else:
                            print(f"Unknown RGB format: size={rgb_size}, expected={rgb_width * rgb_height * 3} or {rgb_width * rgb_height * 2}")
                
                # Receive IR data
                ir_img = None
                if ir_size > 0:
                    ir_data = self._receive_exact(ir_size)
                    if ir_data:
                        ir_array = np.frombuffer(ir_data, dtype=np.uint8)
                        ir_img = ir_array.reshape((ir_height, ir_width))
                
                # Update latest frames with thread safety
                with self.lock:
                    self.latest_depth = depth_img
                    self.latest_rgb = rgb_img
                    self.latest_ir = ir_img
                    self.frame_count += 1
                
                print(f"\rReceived frame {frame_id:04d} | FPS: {self._get_fps():.1f}", end="", flush=True)
                
            except Exception as e:
                print(f"\nError in receive loop: {e}")
                break
        
        print("\nReceive loop ended")
    
    def _receive_exact(self, size: int) -> Optional[bytes]:
        """Receive exactly 'size' bytes from socket"""
        data = b''
        while len(data) < size:
            try:
                chunk = self.socket.recv(size - len(data))
                if not chunk:
                    return None
                data += chunk
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Socket receive error: {e}")
                return None
        return data
    
    def get_latest_frames(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
        """Get the latest depth, RGB, and IR frames"""
        with self.lock:
            return self.latest_depth, self.latest_rgb, self.latest_ir
    
    def _get_fps(self) -> float:
        """Calculate current FPS"""
        elapsed = time.time() - self.start_time
        return self.frame_count / elapsed if elapsed > 0 else 0.0
    
    def is_running(self) -> bool:
        """Check if client is running"""
        return self.running and self.connected

def main():
    """Demo application showing live camera stream"""
    client = CameraStreamClient()
    
    try:
        # Connect to server
        if not client.connect():
            return
        
        # Start streaming
        if not client.start_streaming():
            client.disconnect()
            return
        
        # Create OpenCV windows
        cv2.namedWindow('Live Depth Stream', cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow('Live RGB Stream', cv2.WINDOW_AUTOSIZE)
        cv2.moveWindow('Live Depth Stream', 100, 100)
        cv2.moveWindow('Live RGB Stream', 700, 100)
        
        print("\nLive camera stream viewer started")
        print("Press 'q' to quit, 's' to save frames")
        print("\n3-Zone Danger Detection + Time-to-Collision (TTC) Active:")
        print("  Format: LEFT(distance,TTC) | CENTER(distance,TTC) | RIGHT(distance,TTC)")
        print("  Zone Layout: [30%] [40%] [30%]")
        print("  Thresholds: Left/Right < 1.0m, Center < 1.5m")
        print("  Status: 'safe' or 'warn' + distance + TTC")
        print("  TTC Colors: Green=safe, Orange=TTC<5s, Red=immediate danger")
        print("  Visual: Distance + TTC overlay shown on depth video feed")
        
        if audio_manager and audio_manager.audio_enabled:
            print("\nTTS Audio Warning System Active:")
            print("  - Triggers when TTC ≤ 4 seconds")
            print("  - Sequential warnings: 'Kanan!' (Right), 'Kiri!' (Left), 'Tengah!' (Center)")
            print("  - Language: Indonesian (Bahasa Indonesia)")
            print("  - Audio format: MP3 (cached for bandwidth efficiency)")
            print("  - Cooldown: 2 seconds between same warning combinations")
        else:
            print("\nTTS Audio Warning System: DISABLED")
            print("  Install required packages: pip install gtts pygame pydub")
        print()
        
        save_counter = 0
        
        while True:
            # Get latest frames
            depth_img, rgb_img, ir_img = client.get_latest_frames()
            
            # Perform 3-zone danger detection with TTC calculation
            if depth_img is not None:
                (left_status, left_dist, left_ttc), (center_status, center_dist, center_ttc), (right_status, right_dist, right_ttc) = analyze_danger_zones(depth_img)
                
                # Check for TTC warnings (4 seconds or under)
                if audio_manager and audio_manager.audio_enabled:
                    warning_zones = []
                    
                    # Check each zone for TTC under 4 seconds (in priority order: right, left, center)
                    if right_ttc is not None and right_ttc <= 4.0:
                        warning_zones.append("kanan")  # Right
                    if left_ttc is not None and left_ttc <= 4.0:
                        warning_zones.append("kiri")   # Left  
                    if center_ttc is not None and center_ttc <= 4.0:
                        warning_zones.append("tengah") # Center
                    
                    # Play sequential warnings if any zones have TTC <= 4 seconds
                    if warning_zones:
                        audio_manager.play_warning_sequence(warning_zones)
                
                # Format TTC display helper
                def format_ttc(ttc):
                    if ttc is None:
                        return "---"
                    elif ttc < 10:
                        return f"{ttc:.1f}s"
                    else:
                        return f"{ttc:.0f}s"
                
                # Print concise warning line for each frame with distances and TTC
                left_display = f"{left_status}({left_dist:.2f}m,{format_ttc(left_ttc)})"
                center_display = f"{center_status}({center_dist:.2f}m,{format_ttc(center_ttc)})"
                right_display = f"{right_status}({right_dist:.2f}m,{format_ttc(right_ttc)})"
                print(f"\r{left_display} | {center_display} | {right_display}", end="", flush=True)
            
            # Display depth image
            if depth_img is not None:
                # Create mask for valid depth values (exclude 0 and very high values)
                # Typical depth camera range is 0.3m to 10m, so values close to 0 or max uint16 are invalid
                valid_mask = (depth_img > 100) & (depth_img < 60000)  # Adjust thresholds as needed
                
                # Create output image
                depth_colored = np.zeros((depth_img.shape[0], depth_img.shape[1], 3), dtype=np.uint8)
                
                if np.any(valid_mask):
                    # Process only valid depth values
                    valid_depth = depth_img[valid_mask]
                    
                    # Normalize only the valid range for better contrast
                    min_valid = np.min(valid_depth)
                    max_valid = np.max(valid_depth)
                    
                    # Create normalized depth image
                    depth_processed = np.zeros_like(depth_img, dtype=np.float32)
                    depth_processed[valid_mask] = (depth_img[valid_mask] - min_valid) / (max_valid - min_valid)
                    
                    # Convert to 8-bit and invert (closer = higher values = red)
                    depth_norm = (depth_processed * 255).astype(np.uint8)
                    depth_inverted = 255 - depth_norm
                    
                    # Apply colormap
                    depth_colored = cv2.applyColorMap(depth_inverted, cv2.COLORMAP_JET)
                    
                    # Set invalid areas to deep blue/black
                    depth_colored[~valid_mask] = [30, 0, 0]  # Deep blue in BGR format
                    
                    # Draw zone boundaries and status indicators
                    height, width = depth_colored.shape[:2]
                    
                    # Define zone boundaries (30% left, 40% center, 30% right)
                    left_end = int(width * 0.3)
                    center_end = int(width * 0.7)
                    
                    # Draw vertical lines to separate zones
                    cv2.line(depth_colored, (left_end, 0), (left_end, height), (255, 255, 255), 2)
                    cv2.line(depth_colored, (center_end, 0), (center_end, height), (255, 255, 255), 2)
                    
                    # Add zone labels and status colors
                    if 'left_status' in locals() and 'center_status' in locals() and 'right_status' in locals() and 'left_dist' in locals() and 'left_ttc' in locals():
                        # Color coding: Green for safe, Red for warn, Orange for TTC warning
                        def get_zone_color(status, ttc):
                            if status == "warn":
                                return (0, 0, 255)  # Red for immediate danger
                            elif ttc is not None and ttc < 5.0:
                                return (0, 165, 255)  # Orange for TTC warning
                            else:
                                return (0, 255, 0)  # Green for safe
                        
                        left_color = get_zone_color(left_status, left_ttc)
                        center_color = get_zone_color(center_status, center_ttc)
                        right_color = get_zone_color(right_status, right_ttc)
                        
                        # Add colored rectangles at top to show zone status (taller for TTC info)
                        cv2.rectangle(depth_colored, (5, 5), (left_end - 5, 65), left_color, -1)
                        cv2.rectangle(depth_colored, (left_end + 5, 5), (center_end - 5, 65), center_color, -1)
                        cv2.rectangle(depth_colored, (center_end + 5, 5), (width - 5, 65), right_color, -1)
                        
                        # Helper function to format TTC display
                        def format_ttc_display(ttc):
                            if ttc is None:
                                return "TTC: ---"
                            elif ttc < 10:
                                return f"TTC: {ttc:.1f}s"
                            else:
                                return f"TTC: {ttc:.0f}s"
                        
                        # Add text labels with distances and TTC
                        cv2.putText(depth_colored, "LEFT", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(depth_colored, f"{left_dist:.2f}m", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(depth_colored, format_ttc_display(left_ttc), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                        
                        cv2.putText(depth_colored, "CENTER", (left_end + 10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(depth_colored, f"{center_dist:.2f}m", (left_end + 10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(depth_colored, format_ttc_display(center_ttc), (left_end + 10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                        
                        cv2.putText(depth_colored, "RIGHT", (center_end + 10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(depth_colored, f"{right_dist:.2f}m", (center_end + 10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(depth_colored, format_ttc_display(right_ttc), (center_end + 10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                else:
                    # If no valid depth data, make everything deep blue/black
                    depth_colored[:, :] = [30, 0, 0]  # Deep blue in BGR
                
                cv2.imshow('Live Depth Stream', depth_colored)
            
            # Display RGB image
            if rgb_img is not None:
                cv2.imshow('Live RGB Stream', rgb_img)
            
            # Handle keyboard input
            key = cv2.waitKey(30) & 0xFF
            
            if key == ord('q'):
                print("\nQuitting...")
                break
            elif key == ord('s'):
                # Save current frames
                if depth_img is not None:
                    # Apply the same depth processing as in display
                    valid_mask = (depth_img > 100) & (depth_img < 60000)
                    depth_colored = np.zeros((depth_img.shape[0], depth_img.shape[1], 3), dtype=np.uint8)
                    
                    if np.any(valid_mask):
                        valid_depth = depth_img[valid_mask]
                        min_valid = np.min(valid_depth)
                        max_valid = np.max(valid_depth)
                        
                        depth_processed = np.zeros_like(depth_img, dtype=np.float32)
                        depth_processed[valid_mask] = (depth_img[valid_mask] - min_valid) / (max_valid - min_valid)
                        
                        depth_norm = (depth_processed * 255).astype(np.uint8)
                        depth_inverted = 255 - depth_norm
                        depth_colored = cv2.applyColorMap(depth_inverted, cv2.COLORMAP_JET)
                        depth_colored[~valid_mask] = [30, 0, 0]  # Deep blue for invalid areas
                    else:
                        depth_colored[:, :] = [30, 0, 0]  # Deep blue
                    
                    cv2.imwrite(f"live_depth_{save_counter:04d}.png", depth_colored)
                if rgb_img is not None:
                    cv2.imwrite(f"live_rgb_{save_counter:04d}.png", rgb_img)
                print(f"\nSaved frames {save_counter:04d}")
                save_counter += 1
            
            time.sleep(0.01)  # Small delay
    
    except KeyboardInterrupt:
        print("\nReceived Ctrl+C")
    
    finally:
        # Cleanup
        client.disconnect()
        cv2.destroyAllWindows()
        print("Live stream client stopped")

if __name__ == "__main__":
    main()
