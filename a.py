import cv2
import cv2.aruco as aruco
import os

video_path = '/home/aviral/lnt/aruco/lnt.mp4' 
temp_output = 'temp_no_audio.mp4'
final_output = 'final_landing_with_audio.mp4'

cap = cv2.VideoCapture(video_path)

frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

# Changed 'avc1' to 'mp4v' to avoid the hardware encoder error
fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
out = cv2.VideoWriter(temp_output, fourcc, fps, (frame_width, frame_height))

aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_5X5_50)
parameters = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, parameters)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.normalize(frame, None, 0, 255, cv2.NORM_MINMAX)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is not None:
        aruco.drawDetectedMarkers(frame, corners, ids)
        for i in range(len(ids)):
            if ids[i][0] == 17:
                c = corners[i][0]
                x, y = int(c[0][0]), int(c[0][1])
                cv2.putText(frame, "marker detected ....landing", (x, y - 15), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    out.write(frame)
    cv2.imshow('Processing...', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
out.release()
cv2.destroyAllWindows()

# Final FFmpeg command handles the conversion to H.264 (libx264) and YUV420P
if os.path.exists(temp_output):
    print("Merging audio and converting for WhatsApp...")
    ffmpeg_cmd = (
        f"ffmpeg -y -i {temp_output} -i {video_path} "
        f"-map 0:v:0 -map 1:a:0? -c:v libx264 -pix_fmt yuv420p "
        f"-c:a aac -shortest {final_output}"
    )
    os.system(ffmpeg_cmd)
    
    if os.path.exists(final_output):
        os.remove(temp_output)
        print(f"Success! Final video: {final_output}")
else:
    print("Error: Temporary video file was not created.")