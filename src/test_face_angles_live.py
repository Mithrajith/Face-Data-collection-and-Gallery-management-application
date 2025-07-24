import cv2
import numpy as np
import mediapipe as mp
from ultralytics import YOLO
from quality_checker import VideoQualityChecker

# --- CONFIG ---
YOLO_MODEL_PATH = 'yolo/weights/yolo11n-face.pt'  # Update this path

# --- Initialize ---
checker = VideoQualityChecker(YOLO_MODEL_PATH)

# --- Helper for overlay ---
def draw_face_angle_overlay(frame, bbox, angle_label, angle_count):
    x1, y1, x2, y2 = bbox
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    label = f"{angle_label} | {angle_count}"
    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

# --- Main loop ---


cap = cv2.VideoCapture(0)

# Get video properties for output
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
if fps == 0 or np.isnan(fps):
    fps = 24  # fallback default

# Define the codec and create VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('test_result.mp4', fourcc, fps, (frame_width, frame_height))

# Accumulate unique face angles across all frames
global_face_angles_seen = set()

while True:
    if 'start_time' not in locals():
        import time
        start_time = time.time()

    ret, frame = cap.read()
    if not ret:
        break

    # Detect faces with YOLO
    results = checker.yolo_model(frame, conf=0.7)
    face_bboxes = []
    face_angle_labels = []
    frame_angles_seen = set()

    if len(results) > 0 and hasattr(results[0], 'boxes') and len(results[0].boxes) > 0:
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            bbox = (x1, y1, x2, y2)
            face_img = frame[y1:y2, x1:x2]
            if face_img.size == 0:
                continue
            # Estimate face angle
            angle_label, yaw, pitch, roll = checker.estimate_face_pose(frame, bbox)
            print(f"[DEBUG] Angle: {angle_label}, Yaw: {yaw:.2f}, Pitch: {pitch:.2f}, Roll: {roll:.2f}")
            global_face_angles_seen.add(angle_label)
            frame_angles_seen.add(angle_label)
            face_bboxes.append(bbox)
            face_angle_labels.append(angle_label)

    # Draw overlays
    for bbox, angle_label in zip(face_bboxes, face_angle_labels):
        draw_face_angle_overlay(frame, bbox, angle_label, len(global_face_angles_seen))

    # Show info
    cv2.putText(frame, f"Unique face angles detected: {len(global_face_angles_seen)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    out.write(frame)

    # Stop after 60 seconds or on keypress
    if time.time() - start_time > 20:
        print("[INFO] 60 seconds elapsed. Stopping recording.")
        break
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("[INFO] 'q' pressed. Stopping recording.")
        break

cap.release()
out.release()

# Print result in terminal
print("\n[RESULT] Unique face angles detected in 60 seconds:")
if global_face_angles_seen:
    print(", ".join(sorted(global_face_angles_seen)))
else:
    print("No face angles detected.")
