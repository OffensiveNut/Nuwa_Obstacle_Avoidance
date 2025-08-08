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
from typing import Optional, Tuple

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
        
        save_counter = 0
        
        while True:
            # Get latest frames
            depth_img, rgb_img, ir_img = client.get_latest_frames()
            
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
