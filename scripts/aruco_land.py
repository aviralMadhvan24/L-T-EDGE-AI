import cv2
import numpy as np
from pymavlink import mavutil
import time
import math

# 1. Connection & Camera Setup
gst_str = ("udpsrc port=5600 ! application/x-rtp, payload=96 ! "
           "rtph264depay ! avdec_h264 ! videoconvert ! "
           "video/x-raw, format=BGR ! appsink drop=true sync=false")
cap = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)

vehicle = mavutil.mavlink_connection('udp:127.0.0.1:14550')
vehicle.wait_heartbeat()
print("Connected! Starting search from extreme corner (20,20)...")

aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
parameters = cv2.aruco.DetectorParameters_create()

start_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret: continue

    # CRITICAL: Keep connection alive
    vehicle.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, 
                               mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

    if ids is not None:
        # --- PHASE 2: PRECISION LANDING ---
        c = corners[0][0]
        m_x, m_y = int((c[0][0] + c[2][0]) / 2), int((c[0][1] + c[2][1]) / 2)
        i_x, i_y = frame.shape[1]//2, frame.shape[0]//2

        # Send target offsets to PX4 Landing Target estimator
        # Scaling factor 0.0015 converts pixel error to angle/positional shift
        vehicle.mav.landing_target_send(
            0, 0, mavutil.mavlink.MAV_FRAME_BODY_NED,
            (m_x - i_x) * 0.0015, (m_y - i_y) * 0.0015, 0, 0, 0)
        
        cv2.circle(frame, (m_x, m_y), 15, (0, 255, 0), -1)
        cv2.putText(frame, "TARGET ACQUIRED: LANDING", (10, 30), 1, 1.5, (0, 255, 0), 2)
    else:
        # --- PHASE 1: INWARD SPIRAL SEARCH ---
        t = time.time() - start_time
        
        # Spiral parameters
        # Distance from (20,20) to (0,0) is approx 28m
        max_r = 28.0 
        shrink_rate = 0.3   # How fast it moves toward center
        rotation_speed = 0.4 
        
        current_r = max(0, max_r - (shrink_rate * t))
        angle = rotation_speed * t
        
        # Coordinate Translation:
        # World (0,0) is Local (-20, -20)
        target_x = (current_r * math.cos(angle)) - 20
        target_y = (current_r * math.sin(angle)) - 20

        vehicle.mav.set_position_target_local_ned_send(
            0, vehicle.target_system, vehicle.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED, 0b110111111000, 
            target_x, target_y, -6, # Fly at 6m altitude for wide FOV
            0, 0, 0, 0, 0, 0, 0, 0)
        
        cv2.putText(frame, f"SEARCHING: R={round(current_r,1)}", (10, 30), 1, 1.5, (0, 0, 255), 2)

    cv2.imshow('Precision Landing Feed', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()