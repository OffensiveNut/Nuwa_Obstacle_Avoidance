#ifndef CAMERA_STREAM_INTERFACE_H
#define CAMERA_STREAM_INTERFACE_H

#include <memory>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <string>

struct StreamFrameData {
    // Frame metadata
    uint64_t timestamp;
    uint32_t frame_id;
    uint32_t width;
    uint32_t height;
    
    // Data sizes
    uint32_t depth_size;
    uint32_t rgb_size;
    uint32_t ir_size;
    
    // Data pointers (will point to shared memory)
    uint8_t* depth_data;
    uint8_t* rgb_data;
    uint8_t* ir_data;
    
    // Frame validity
    bool has_depth;
    bool has_rgb;
    bool has_ir;
};

class CameraStreamInterface {
public:
    CameraStreamInterface();
    ~CameraStreamInterface();
    
    // Initialize the shared memory interface
    bool initialize(const std::string& shared_memory_name = "angstrong_camera_stream");
    
    // Update frame data (called from camera callback)
    void updateFrame(const void* depth_data, uint32_t depth_size,
                    const void* rgb_data, uint32_t rgb_size,
                    const void* ir_data, uint32_t ir_size,
                    uint32_t width, uint32_t height);
    
    // Get latest frame (for Python interface)
    bool getLatestFrame(StreamFrameData& frame_data);
    
    // Status and control
    bool isActive() const { return active_; }
    uint32_t getFrameCount() const { return frame_count_; }
    
    // Cleanup
    void shutdown();

private:
    struct SharedMemoryLayout {
        // Header with metadata
        volatile uint64_t timestamp;
        volatile uint32_t frame_id;
        volatile uint32_t width;
        volatile uint32_t height;
        volatile uint32_t depth_size;
        volatile uint32_t rgb_size;
        volatile uint32_t ir_size;
        volatile bool has_new_frame;
        volatile bool has_depth;
        volatile bool has_rgb;
        volatile bool has_ir;
        
        // Data follows after header
        uint8_t data[0];  // Flexible array member
    };
    
    void* shared_memory_;
    SharedMemoryLayout* layout_;
    size_t shared_memory_size_;
    std::string shared_memory_name_;
    int shared_memory_fd_;
    
    std::mutex frame_mutex_;
    std::atomic<bool> active_;
    std::atomic<uint32_t> frame_count_;
    
    static const size_t MAX_FRAME_SIZE = 640 * 480 * 4; // Max size per channel
    static const size_t SHARED_MEMORY_SIZE = sizeof(SharedMemoryLayout) + (MAX_FRAME_SIZE * 3); // depth + rgb + ir
};

// C interface for easier Python integration
extern "C" {
    // Create/destroy interface
    void* camera_stream_create();
    void camera_stream_destroy(void* interface);
    
    // Initialize
    int camera_stream_initialize(void* interface, const char* shared_memory_name);
    
    // Update frame (called from camera callback)
    int camera_stream_update_frame(void* interface,
                                  const void* depth_data, uint32_t depth_size,
                                  const void* rgb_data, uint32_t rgb_size,
                                  const void* ir_data, uint32_t ir_size,
                                  uint32_t width, uint32_t height);
    
    // Get frame info for Python
    int camera_stream_get_frame_info(void* interface,
                                    uint64_t* timestamp,
                                    uint32_t* frame_id,
                                    uint32_t* width,
                                    uint32_t* height,
                                    uint32_t* depth_size,
                                    uint32_t* rgb_size,
                                    uint32_t* ir_size);
    
    // Get frame data
    int camera_stream_get_depth_data(void* interface, void* buffer, uint32_t buffer_size);
    int camera_stream_get_rgb_data(void* interface, void* buffer, uint32_t buffer_size);
    int camera_stream_get_ir_data(void* interface, void* buffer, uint32_t buffer_size);
    
    // Status
    int camera_stream_is_active(void* interface);
    uint32_t camera_stream_get_frame_count(void* interface);
    
    // Shutdown
    void camera_stream_shutdown(void* interface);
}

#endif // CAMERA_STREAM_INTERFACE_H
