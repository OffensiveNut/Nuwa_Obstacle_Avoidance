/**
 * @file      PythonStreamServer.h
 * @brief     Header for Python streaming server to expose camera data
 *
 * Copyright (c) 2025 Custom Implementation
 *
 * @author    Custom Developer
 * @date      2025/08/09
 * @version   1.0
 */

#ifndef PYTHON_STREAM_SERVER_H
#define PYTHON_STREAM_SERVER_H

#include <thread>
#include <mutex>
#include <atomic>
#include <memory>
#include <queue>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include "as_camera_sdk_def.h"

struct StreamFrame {
    uint64_t timestamp;
    uint32_t frame_id;
    
    // Depth data
    uint32_t depth_width;
    uint32_t depth_height;
    uint32_t depth_size;
    std::shared_ptr<uint8_t> depth_data;
    
    // RGB data
    uint32_t rgb_width;
    uint32_t rgb_height;
    uint32_t rgb_size;
    std::shared_ptr<uint8_t> rgb_data;
    
    // IR data (optional)
    uint32_t ir_width;
    uint32_t ir_height;
    uint32_t ir_size;
    std::shared_ptr<uint8_t> ir_data;
};

class PythonStreamServer {
public:
    PythonStreamServer(int port = 8888);
    ~PythonStreamServer();
    
    bool start();
    void stop();
    
    // Called from camera callback to push new frame data
    void pushFrame(const AS_SDK_Data_s *pstData);
    
    bool isRunning() const { return m_running; }
    int getConnectedClients() const { return m_connected_clients; }

private:
    void serverThread();
    void clientHandler(int client_socket);
    
    bool sendFrameToClient(int client_socket, const StreamFrame& frame);
    StreamFrame convertToStreamFrame(const AS_SDK_Data_s *pstData);
    
    int m_port;
    int m_server_socket;
    std::atomic<bool> m_running;
    std::atomic<int> m_connected_clients;
    
    std::thread m_server_thread;
    std::mutex m_frame_mutex;
    std::queue<StreamFrame> m_frame_queue;
    
    static const size_t MAX_QUEUE_SIZE = 10;
    uint32_t m_frame_counter;
};

#endif // PYTHON_STREAM_SERVER_H
