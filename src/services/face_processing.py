import os
import cv2
import numpy as np
from typing import List
from ultralytics import YOLO

from config.settings import DEFAULT_YOLO_PATH

def extract_frames(video_path: str, output_dir: str, max_frames: int = 1000, interval: int = 1) -> List[str]:
    """
    Extract frames from a video at specified intervals
    
    Args:
        video_path: Path to the video file
        output_dir: Directory to save extracted frames
        max_frames: Maximum number of frames to extract
        interval: Extract a frame every 'interval' frames
    
    Returns:
        List of paths to extracted frames
    """
    print(f"Extracting frames from: {video_path}")
    print(f"Output directory: {output_dir}")
    print(f"Max frames: {max_frames}, Interval: {interval}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return []
    
    # Get video properties for debugging
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 0
    print(f"Video properties: {total_frames} frames, {fps} FPS, {duration:.2f} seconds")
    
    frame_paths = []
    frame_count = 0
    saved_count = 0
    max_read_attempts = total_frames + 100  # Safety limit to prevent infinite loops
    read_attempts = 0
    
    while saved_count < max_frames and read_attempts < max_read_attempts:
        ret, frame = cap.read()
        read_attempts += 1
        
        if not ret:
            print(f"End of video reached at frame {frame_count} (attempt {read_attempts})")
            break
            
        if frame_count % interval == 0:
            # Save frame as image
            frame_path = os.path.join(output_dir, f"frame_{saved_count:03d}.jpg")
            success = cv2.imwrite(frame_path, frame)
            if success:
                frame_paths.append(frame_path)
                saved_count += 1
                if saved_count % 10 == 0:  # Log every 10th frame
                    print(f"Saved frame {saved_count}/{max_frames}")
            else:
                print(f"Failed to save frame {frame_count} to {frame_path}")
            
        frame_count += 1
    
    cap.release()
    print(f"Frame extraction complete: {len(frame_paths)} frames saved")
    return frame_paths

def detect_and_crop_faces(image_path: str, output_dir: str, yolo_path: str = DEFAULT_YOLO_PATH) -> List[str]:
    """
    Detect, crop, and preprocess faces from an image using YOLO
    
    Args:
        image_path: Path to the input image
        output_dir: Directory to save preprocessed face images
        yolo_path: Path to YOLO model weights
        
    Returns:
        List of paths to preprocessed face images
    """
    print(f"Processing image: {image_path}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Load YOLO model
    model = YOLO(yolo_path)
    
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image {image_path}")
        return []
    
    # Detect faces
    results = model(img)
    
    print(f"YOLO detected {sum(len(r.boxes) for r in results)} faces in {image_path}")
    
    face_paths = []
    for i, result in enumerate(results):
        for j, box in enumerate(result.boxes):
            # Get bounding box coordinates
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # Add some padding around the face
            h, w = img.shape[:2]
            face_w = x2 - x1
            face_h = y2 - y1
            pad_x = int(face_w * 0.2)
            pad_y = int(face_h * 0.2)
            x1 = max(0, x1 - pad_x)
            y1 = max(0, y1 - pad_y)
            x2 = min(w, x2 + pad_x)
            y2 = min(h, y2 + pad_y)
            
            print(f"Face {j} dimensions before padding: {x2-x1}x{y2-y1}")
            print(f"Face {j} dimensions after padding: {max(0, x1-pad_x)}-{min(w, x2+pad_x)}x{max(0, y1-pad_y)}-{min(h, y2+pad_y)}")
            
            # Skip if face coordinates are too small
            if (x2 - x1) < 32 or (y2 - y1) < 32:
                print(f"Skipping face {j} in {image_path} - too small ({x2-x1}x{y2-y1})")
                continue
                
            # Crop face
            face = img[y1:y2, x1:x2]
            
            # Skip empty faces or irregular shapes
            if face.size == 0 or face.shape[0] <= 0 or face.shape[1] <= 0:
                print(f"Skipping face {j} in {image_path} - invalid dimensions")
                continue
            
            # Save original cropped face for reference
            img_name = os.path.basename(image_path)
            original_face_path = os.path.join(output_dir, f"{os.path.splitext(img_name)[0]}_face_orig_{j}.jpg")
            # cv2.imwrite(original_face_path, face)
            
            # Preprocess face properly for LightCNN:
            
            # 1. Convert to grayscale
            if len(face.shape) == 3:  # Color image
                gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
            else:  # Already grayscale
                gray = face
                
            # 2. Resize to 128x128 (LightCNN input size)
            # Use INTER_LANCZOS4 for best quality when downsizing
            resized = cv2.resize(gray, (128, 128), interpolation=cv2.INTER_LANCZOS4)
            
            # 3. Normalize pixel values to [0, 1] range
            normalized = resized.astype(np.float32) / 255.0
            
            # 4. Apply histogram equalization for better contrast
            equalized = cv2.equalizeHist(resized)
            
            # 5. Save preprocessed face
            face_path = os.path.join(output_dir, f"{os.path.splitext(img_name)[0]}_face_{j}.jpg")
            cv2.imwrite(face_path, equalized)
            face_paths.append(face_path)
    
    return face_paths
