/**
 * @file      PythonStreamServer.cpp
 * @brief     Implementation of Python streaming server
 *
 * Copyright (c) 2025 Custom Implementation
 *
 * @author    Custom Developer
 * @date      2025/08/09
 * @version   1.0
 */

#include "PythonStreamServer.h"
#include <iostream>
#include <cstring>
#include <chrono>
#include <sys/socket.h>

PythonStreamServer::PythonStreamServer(int port) 
    : m_port(port)
    , m_server_socket(-1)
    , m_running(false)
    , m_connected_clients(0)
    , m_frame_counter(0)
{
}

PythonStreamServer::~PythonStreamServer() {
    stop();
}

bool PythonStreamServer::start() {
    if (m_running) {
        return true;
    }
    
    // Create socket
    m_server_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (m_server_socket < 0) {
        std::cerr << "Failed to create socket" << std::endl;
        return false;
    }
    
    // Set socket options
    int opt = 1;
    if (setsockopt(m_server_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        std::cerr << "Failed to set socket options" << std::endl;
        close(m_server_socket);
        return false;
    }
    
    // Bind socket
    struct sockaddr_in address;
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(m_port);
    
    if (bind(m_server_socket, (struct sockaddr*)&address, sizeof(address)) < 0) {
        std::cerr << "Failed to bind socket to port " << m_port << std::endl;
        close(m_server_socket);
        return false;
    }
    
    // Listen for connections
    if (listen(m_server_socket, 3) < 0) {
        std::cerr << "Failed to listen on socket" << std::endl;
        close(m_server_socket);
        return false;
    }
    
    m_running = true;
    m_server_thread = std::thread(&PythonStreamServer::serverThread, this);
    
    std::cout << "Python Stream Server started on port " << m_port << std::endl;
    return true;
}

void PythonStreamServer::stop() {
    if (!m_running) {
        return;
    }
    
    m_running = false;
    
    if (m_server_socket >= 0) {
        close(m_server_socket);
        m_server_socket = -1;
    }
    
    if (m_server_thread.joinable()) {
        m_server_thread.join();
    }
    
    std::cout << "Python Stream Server stopped" << std::endl;
}

void PythonStreamServer::pushFrame(const AS_SDK_Data_s *pstData) {
    if (!m_running || !pstData) {
        return;
    }
    
    StreamFrame frame = convertToStreamFrame(pstData);
    
    std::lock_guard<std::mutex> lock(m_frame_mutex);
    
    // Keep queue size manageable
    while (m_frame_queue.size() >= MAX_QUEUE_SIZE) {
        m_frame_queue.pop();
    }
    
    m_frame_queue.push(frame);
}

void PythonStreamServer::serverThread() {
    while (m_running) {
        struct sockaddr_in client_address;
        socklen_t client_len = sizeof(client_address);
        
        int client_socket = accept(m_server_socket, (struct sockaddr*)&client_address, &client_len);
        
        if (client_socket < 0) {
            if (m_running) {
                std::cerr << "Failed to accept client connection" << std::endl;
            }
            continue;
        }
        
        std::cout << "Python client connected from " << inet_ntoa(client_address.sin_addr) << std::endl;
        
        // Handle client in separate thread
        std::thread client_thread(&PythonStreamServer::clientHandler, this, client_socket);
        client_thread.detach();
    }
}

void PythonStreamServer::clientHandler(int client_socket) {
    m_connected_clients++;
    
    try {
        while (m_running) {
            StreamFrame frame;
            bool has_frame = false;
            
            // Get latest frame
            {
                std::lock_guard<std::mutex> lock(m_frame_mutex);
                if (!m_frame_queue.empty()) {
                    frame = m_frame_queue.front();
                    m_frame_queue.pop();
                    has_frame = true;
                }
            }
            
            if (has_frame) {
                if (!sendFrameToClient(client_socket, frame)) {
                    break; // Client disconnected
                }
            } else {
                // No frame available, wait a bit
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception in client handler: " << e.what() << std::endl;
    } catch (...) {
        std::cerr << "Unknown exception in client handler" << std::endl;
    }
    
    // Clean shutdown
    shutdown(client_socket, SHUT_RDWR);
    close(client_socket);
    m_connected_clients--;
    std::cout << "Python client disconnected" << std::endl;
}

bool PythonStreamServer::sendFrameToClient(int client_socket, const StreamFrame& frame) {
    try {
        // Protocol: Send header first, then data
        struct FrameHeader {
            uint64_t timestamp;
            uint32_t frame_id;
            uint32_t depth_width;
            uint32_t depth_height;
            uint32_t depth_size;
            uint32_t rgb_width;
            uint32_t rgb_height;
            uint32_t rgb_size;
            uint32_t ir_width;
            uint32_t ir_height;
            uint32_t ir_size;
        } header;
        
        header.timestamp = frame.timestamp;
        header.frame_id = frame.frame_id;
        header.depth_width = frame.depth_width;
        header.depth_height = frame.depth_height;
        header.depth_size = frame.depth_size;
        header.rgb_width = frame.rgb_width;
        header.rgb_height = frame.rgb_height;
        header.rgb_size = frame.rgb_size;
        header.ir_width = frame.ir_width;
        header.ir_height = frame.ir_height;
        header.ir_size = frame.ir_size;
        
        // Send header with error checking
        ssize_t sent = send(client_socket, &header, sizeof(header), MSG_NOSIGNAL);
        if (sent != sizeof(header)) {
            return false;
        }
        
        // Send depth data
        if (frame.depth_size > 0 && frame.depth_data) {
            sent = send(client_socket, frame.depth_data.get(), frame.depth_size, MSG_NOSIGNAL);
            if (sent != (ssize_t)frame.depth_size) {
                return false;
            }
        }
        
        // Send RGB data
        if (frame.rgb_size > 0 && frame.rgb_data) {
            sent = send(client_socket, frame.rgb_data.get(), frame.rgb_size, MSG_NOSIGNAL);
            if (sent != (ssize_t)frame.rgb_size) {
                return false;
            }
        }
        
        // Send IR data
        if (frame.ir_size > 0 && frame.ir_data) {
            sent = send(client_socket, frame.ir_data.get(), frame.ir_size, MSG_NOSIGNAL);
            if (sent != (ssize_t)frame.ir_size) {
                return false;
            }
        }
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "Exception sending frame: " << e.what() << std::endl;
        return false;
    } catch (...) {
        std::cerr << "Unknown exception sending frame" << std::endl;
        return false;
    }
}

StreamFrame PythonStreamServer::convertToStreamFrame(const AS_SDK_Data_s *pstData) {
    StreamFrame frame;
    
    auto now = std::chrono::high_resolution_clock::now();
    frame.timestamp = std::chrono::duration_cast<std::chrono::microseconds>(now.time_since_epoch()).count();
    frame.frame_id = ++m_frame_counter;
    
    // Copy depth data
    if (pstData->depthImg.size > 0) {
        frame.depth_width = pstData->depthImg.width;
        frame.depth_height = pstData->depthImg.height;
        frame.depth_size = pstData->depthImg.size;
        frame.depth_data = std::shared_ptr<uint8_t>(new uint8_t[frame.depth_size], std::default_delete<uint8_t[]>());
        memcpy(frame.depth_data.get(), pstData->depthImg.data, frame.depth_size);
    } else {
        frame.depth_width = frame.depth_height = frame.depth_size = 0;
    }
    
    // Copy RGB data
    if (pstData->rgbImg.size > 0) {
        frame.rgb_width = pstData->rgbImg.width;
        frame.rgb_height = pstData->rgbImg.height;
        frame.rgb_size = pstData->rgbImg.size;
        frame.rgb_data = std::shared_ptr<uint8_t>(new uint8_t[frame.rgb_size], std::default_delete<uint8_t[]>());
        memcpy(frame.rgb_data.get(), pstData->rgbImg.data, frame.rgb_size);
    } else {
        frame.rgb_width = frame.rgb_height = frame.rgb_size = 0;
    }
    
    // Copy IR data
    if (pstData->irImg.size > 0) {
        frame.ir_width = pstData->irImg.width;
        frame.ir_height = pstData->irImg.height;
        frame.ir_size = pstData->irImg.size;
        frame.ir_data = std::shared_ptr<uint8_t>(new uint8_t[frame.ir_size], std::default_delete<uint8_t[]>());
        memcpy(frame.ir_data.get(), pstData->irImg.data, frame.ir_size);
    } else {
        frame.ir_width = frame.ir_height = frame.ir_size = 0;
    }
    
    return frame;
}
