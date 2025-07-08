import os
import cv2
import numpy as np
import torch
from typing import List, Dict, Any, Optional, Union, Tuple
from PIL import Image
import torchvision.transforms as transforms
from scipy.spatial.distance import cosine
from ultralytics import YOLO

from models.pydantic_models import GalleryInfo
from config.settings import DEFAULT_MODEL_PATH, DEFAULT_YOLO_PATH
from ml.embeddings import load_model

def get_gallery_info(gallery_path: str) -> Optional[GalleryInfo]:
    """
    Get information about a gallery file
    
    Args:
        gallery_path: Path to gallery file
    
    Returns:
        GalleryInfo or None if file doesn't exist
    """
    if not os.path.exists(gallery_path):
        return None
    
    # Load the gallery file
    try:
        gallery_data = torch.load(gallery_path)
        
        # Handle both formats
        if isinstance(gallery_data, dict) and "identities" in gallery_data:
            identities = gallery_data["identities"]
        else:
            identities = list(gallery_data.keys())
            
        count = len(identities)
        
        return GalleryInfo(
            gallery_path=gallery_path,
            identities=identities,
            count=count
        )
    except Exception as e:
        print(f"Error loading gallery file: {e}")
        return None

def recognize_faces(
    frame: np.ndarray, 
    gallery_paths: Union[str, List[str]], 
    model_path: str = DEFAULT_MODEL_PATH,
    yolo_path: str = DEFAULT_YOLO_PATH,
    threshold: float = 0.45,
    model=None,
    device=None,
    yolo_model=None
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Recognize faces in a given frame using one or more galleries.
    Implements a no-duplicate rule where each identity appears only once.
    
    Args:
        frame: Input image (numpy array in BGR format from cv2)
        gallery_paths: Single gallery path or list of gallery paths
        model_path: Path to LightCNN model
        yolo_path: Path to YOLO face detection model
        threshold: Minimum similarity threshold (0-1)
        model: Pre-loaded model (optional)
        device: Pre-loaded device (optional)
        yolo_model: Pre-loaded YOLO model (optional)
        
    Returns:
        Tuple containing:
            - Annotated frame with bounding boxes and labels
            - List of recognized identities with details
    """
    if isinstance(gallery_paths, str):
        gallery_paths = [gallery_paths]
    
    # Load model and YOLO if not provided
    if model is None or device is None:
        model, device = load_model(model_path)
    
    if yolo_model is None:
        yolo_model = YOLO(yolo_path)
    
    # Load and combine all galleries
    combined_gallery = {}
    for gallery_path in gallery_paths:
        if os.path.exists(gallery_path):
            try:
                gallery_data = torch.load(gallery_path)
                # Handle different gallery formats
                if isinstance(gallery_data, dict):
                    if "identities" in gallery_data:
                        combined_gallery.update(gallery_data["identities"])
                    else:
                        combined_gallery.update(gallery_data)
            except Exception as e:
                print(f"Error loading gallery {gallery_path}: {e}")
    
    if not combined_gallery:
        return frame, []
    
    # Step 1: Detect faces using YOLO
    face_detections = []
    results = yolo_model(frame,conf=0.65)
    
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # Add padding around face
            h, w = frame.shape[:2]
            face_w, face_h = x2 - x1, y2 - y1
            pad_x = int(face_w * 0.2)
            pad_y = int(face_h * 0.2)
            x1 = max(0, x1 - pad_x)
            y1 = max(0, y1 - pad_y)
            x2 = min(w, x2 + pad_x)
            y2 = min(h, y2 + pad_y)
            
            if (x2 - x1) < 32 or (y2 - y1) < 32:
                print(f"  WOULD SKIP FACE  - too small (testing with 5000px threshold)")
                continue
        
            # Extract face image
            face = frame[y1:y2, x1:x2]
            
            # Skip if face is too small
            if face.size == 0 or face.shape[0] < 10 or face.shape[1] < 10:
                continue
                
            # Convert BGR to grayscale PIL image
            face_pil = Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2GRAY))
            
            # Transform for model input
            transform = transforms.Compose([
                transforms.Resize((128, 128)),
                transforms.ToTensor(),
            ])
            
            # Prepare for the model
            face_tensor = transform(face_pil).unsqueeze(0).to(device)
            
            # Extract embedding
            with torch.no_grad():
                _, embedding = model(face_tensor)
                face_embedding = embedding.cpu().squeeze().numpy()
            
            # Find all potential matches above threshold
            matches = []
            for identity, gallery_embedding in combined_gallery.items():
                similarity = 1 - cosine(face_embedding, gallery_embedding)
                if similarity >= threshold:
                    matches.append((identity, similarity))
            
            # Sort matches by similarity (highest first)
            matches.sort(key=lambda x: x[1], reverse=True)
            
            face_detections.append({
                "bbox": (x1, y1, x2, y2),
                "matches": matches,
                "embedding": face_embedding
            })
    
    # Step 2: Assign identities without duplicates - using greedy approach
    face_detections.sort(key=lambda x: x["matches"][0][1] if x["matches"] else 0, reverse=True)
    
    assigned_identities = set()
    detected_faces = []
    
    for face in face_detections:
        x1, y1, x2, y2 = face["bbox"]
        matches = face["matches"]
        
        # Find the best non-assigned match
        best_match = None
        best_score = 0.0
        
        for identity, score in matches:
            if identity not in assigned_identities:
                best_match = identity
                best_score = float(score)
                break
        
        # Store recognition result
        if best_match:
            detected_faces.append({
                "identity": best_match,
                "similarity": best_score,
                "bounding_box": [int(x1), int(y1), int(x2), int(y2)]
            })
            assigned_identities.add(best_match)
        else:
            # No match found - mark as unknown
            detected_faces.append({
                "identity": "Unknown",
                "similarity": 0.0,
                "bounding_box": [int(x1), int(y1), int(x2), int(y2)]
            })
    
    # Step 3: Draw annotations as the final step
    result_img = frame.copy()
    
    for face_info in detected_faces:
        identity = face_info["identity"]
        similarity = face_info["similarity"]
        x1, y1, x2, y2 = face_info["bounding_box"]
        
        # Choose color based on whether it's a known or unknown face
        color = (0, 255, 0) if identity != "Unknown" else (0, 0, 255)
        
        # Draw bounding box
        cv2.rectangle(result_img, (x1, y1), (x2, y2), color, 2)
        
        # Draw label
        label = f"{identity} ({similarity:.2f})" if identity != "Unknown" else "Unknown"
        
        # Create slightly darker shade for text background
        text_bg_color = (int(color[0] * 0.7), int(color[1] * 0.7), int(color[2] * 0.7))
        
        # Get text size for better positioning
        text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        text_w, text_h = text_size
        
        # Draw text background
        cv2.rectangle(result_img, 
                     (x1, y1 - text_h - 8), 
                     (x1 + text_w, y1), 
                     text_bg_color, -1)
        
        # Draw text
        cv2.putText(result_img, 
                   label, 
                   (x1, y1 - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, (255, 255, 255), 2)
    
    return result_img, detected_faces
