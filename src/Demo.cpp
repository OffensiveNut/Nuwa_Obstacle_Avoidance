/**
 * @file      Demo.cpp
 * @brief     angstrong camera service.
 *
 * Copyright (c) 2023 Angstrong Tech.Co.,Ltd
 *
 * @author    Angstrong SDK develop Team
 * @date      2023/02/15
 * @version   1.0

 */

#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <thread>
#include <signal.h>
#include <malloc.h>
#include <string.h>
#include <iostream>
#include <string>
#include <memory>

#include "Logger.h"
#include "as_camera_sdk_api.h"
#include "as_camera_sdk_def.h"
#include "common.h"
#include "Demo.h"

#ifdef CFG_X11_ON
#include <X11/Xlib.h>
#endif

Demo::Demo()
{
#ifdef CFG_X11_ON
    XInitThreads();
#endif
    
    // Initialize Python stream server (C++11 compatible)
    m_python_server.reset(new PythonStreamServer(8888));
    if (m_python_server->start()) {
        LOG(INFO) << "Python stream server started on port 8888" << std::endl;
    } else {
        LOG(ERROR) << "Failed to start Python stream server" << std::endl;
    }
}

Demo::~Demo()
{
    // Stop Python stream server
    if (m_python_server) {
        m_python_server->stop();
        m_python_server.reset();
    }
}

int Demo::start()
{
    int ret = 0;
    if (server == nullptr) {
        server = new CameraSrv(this);
        ret = server->start();
        if (ret != 0) {
            LOG(ERROR) << "start server failed" << std::endl;
        }
    }

    return ret;
}

void Demo::stop()
{
    /* stop streaming and close the camera */
    if (server != nullptr) {
        server->stop();
        /* it will stop the hotplug monitor */
        delete server;
        server = nullptr;
    }

    /* free the map */
    m_camera_map.erase(m_camera_map.begin(), m_camera_map.end());
}

void Demo::display(bool enable)
{
    for (auto it = m_camera_map.begin(); it != m_camera_map.end(); it++) {
        it->second->enableDisplay(enable);
    }
}

bool Demo::getDisplayStatus()
{
    bool status = false;
    for (auto it = m_camera_map.begin(); it != m_camera_map.end(); it++) {
        status = it->second->getDisplayStatus();
    }
    return status;
}

void Demo::saveImage()
{
    for (auto it = m_camera_map.begin(); it != m_camera_map.end(); it++) {
        it->second->enableSaveImage(true);
    }
}

void Demo::logFps(bool enable)
{
    m_logfps = enable;
}

bool Demo::getLogFps()
{
    return m_logfps;
}

int Demo::onCameraAttached(AS_CAM_PTR pCamera, const AS_SDK_CAM_MODEL_E &cam_type)
{
    LOG(INFO) << "camera attached" << std::endl;
    m_camera_map.insert(std::make_pair(pCamera, std::make_shared<Camera>(pCamera, cam_type)));

    bool is_displaying = false;
    for (auto it = m_camera_map.begin(); it != m_camera_map.end(); it++) {
        if (it->second->getDisplayStatus() == true) {
            is_displaying = true;
            break;
        }
    }
    if (is_displaying) {
        for (auto it = m_camera_map.begin(); it != m_camera_map.end(); it++) {
            it->second->enableDisplay(is_displaying);
        }
    }

#ifdef __linux__
    /* nuwa camera whether match usb device.
       If it is a virtual machine, do not match it. */
    if ((cam_type == AS_SDK_CAM_MODEL_NUWA_XB40) ||
        (cam_type == AS_SDK_CAM_MODEL_NUWA_X100) ||
        (cam_type == AS_SDK_CAM_MODEL_NUWA_HP60) ||
        (cam_type == AS_SDK_CAM_MODEL_NUWA_HP60V)) {
        extern int AS_Nuwa_SetUsbDevMatch(bool is_match);
        AS_Nuwa_SetUsbDevMatch(!virtualMachine());
        // AS_Nuwa_SetUsbDevMatch(false);
    }
#endif

    return 0;
}

int Demo::onCameraDetached(AS_CAM_PTR pCamera)
{
    LOG(INFO) << "camera detached" << std::endl;
    auto camIt = m_camera_map.find(pCamera);
    if (camIt != m_camera_map.end()) {
        m_camera_map.erase(pCamera);
    }

    return 0;
}

int Demo::onCameraOpen(AS_CAM_PTR pCamera)
{
    // int ret = 0;
    LOG(INFO) << "camera opened" << std::endl;
    auto camIt = m_camera_map.find(pCamera);
    if (camIt != m_camera_map.end()) {
        camIt->second->init();
    }
    // ret = AS_SDK_SetTimeStampType(pCamera, AS_TIME_STAMP_TYPE_STEADY_CLOCK);
    // if (ret != 0) {
    //     LOG(WARN) << "fail to set time stamp type" << std::endl;
    // }

    // AS_STREAM_Param_s depthParam = {
    //     .width = 160,
    //     .height = 120,
    //     .fps = 10,
    // };
    // AS_STREAM_Param_s rgbParam = {
    //     .width = 640,
    //     .height = 480,
    //     .fps = 10,
    // };
    // AS_SDK_SetStreamParam(pCamera, AS_MEDIA_TYPE_DEPTH, &depthParam);
    // AS_SDK_SetStreamParam(pCamera, AS_MEDIA_TYPE_RGB, &rgbParam);
    return 0;
}

int Demo::onCameraClose(AS_CAM_PTR pCamera)
{
    LOG(INFO) << "camera closed" << std::endl;
    return 0;
}

int Demo::onCameraStart(AS_CAM_PTR pCamera)
{
    LOG(INFO) << "camera start streaming" << std::endl;
    return 0;
}

int Demo::onCameraStop(AS_CAM_PTR pCamera)
{
    LOG(INFO) << "camera stop streaming" << std::endl;
    return 0;
}

void Demo::onCameraNewFrame(AS_CAM_PTR pCamera, const AS_SDK_Data_s *pstData)
{
    std::string serialno = "";
    std::string info = "";

    AS_CAM_ATTR_S attr;
    auto camIt = m_camera_map.find(pCamera);
    if (camIt != m_camera_map.end()) {
        if (m_logfps) {
            camIt->second->checkFps();
        }
        camIt->second->getSerialNo(serialno);
        camIt->second->getCameraAttrs(attr);
        camIt->second->saveImage(pstData);

        if (attr.type == AS_CAMERA_ATTR_LNX_USB) {
            info.append(std::to_string(attr.attr.usbAttrs.bnum) + ":" + attr.attr.usbAttrs.port_numbers);
        } else if (attr.type == AS_CAMERA_ATTR_NET) {
            info.append("_" + std::string(attr.attr.netAttrs.ip_addr));
        }
        camIt->second->displayImage(serialno, info, pstData);
        
        // Push frame to Python stream server
        if (m_python_server && m_python_server->isRunning()) {
            m_python_server->pushFrame(pstData);
        }
    }
}

void Demo::onCameraNewMergeFrame(AS_CAM_PTR pCamera, const AS_SDK_MERGE_s *pstData)
{
    std::string serialno = "";
    std::string info = "";

    AS_CAM_ATTR_S attr;
    auto camIt = m_camera_map.find(pCamera);
    if (camIt != m_camera_map.end()) {
        if (m_logfps) {
            camIt->second->checkFps();
        }
        camIt->second->getSerialNo(serialno);
        camIt->second->getCameraAttrs(attr);
        camIt->second->saveMergeImage(pstData);

        if (attr.type == AS_CAMERA_ATTR_LNX_USB) {
            info.append(std::to_string(attr.attr.usbAttrs.bnum) + ":" + attr.attr.usbAttrs.port_numbers);
        } else if (attr.type == AS_CAMERA_ATTR_NET) {
            info.append(std::to_string(attr.attr.netAttrs.port));
        }

        camIt->second->displayMergeImage(serialno, info, pstData);
    }
}

void Demo::logCfgParameter()
{
    for (auto it = m_camera_map.begin(); it != m_camera_map.end(); it++) {
        AS_SDK_LogCameraCfg(it->first);
    }
}

#ifdef __linux__
bool Demo::virtualMachine()
{
    int cnt = 0;
    char szCnt[8];
    FILE *fp = nullptr;

    char cmd[128];
    snprintf(cmd, sizeof(cmd) - 1, R"(lscpu | grep "Hypervisor vendor" | wc -l)");
    fp = popen(cmd, "r");
    if (fgets(szCnt, sizeof(szCnt), fp) != nullptr) {
        if (strlen(szCnt) != 0) {
            cnt = std::stoi(szCnt);
        }
    }
    pclose(fp);
    fp = nullptr;
    if (cnt == 0) {
        return false;
    } else {
        return true;
    }
}
#endif

