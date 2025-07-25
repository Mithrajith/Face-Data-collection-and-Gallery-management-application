import os
import cv2
import numpy as np
import torch
from tqdm import tqdm
import random
from PIL import Image
import pandas as pd
from scipy.spatial.distance import cosine
from ultralytics import YOLO

from ml.embeddings import load_model, extract_embedding, transform
from utils.image_utils import augment_face_image


def create_gallery(model_path, data_dir, output_path, augment_ratio, augs_per_image=4):
    """Create a face recognition gallery from preprocessed face images"""
    # Load model
    model, device = load_model(model_path)
    
    # Create gallery dictionary
    gallery = {}
    
    # Process each identity folder
    identities = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    print(f"Found {len(identities)} identities")
    
    for identity in tqdm(identities, desc="Processing identities"):
        identity_dir = os.path.join(data_dir, identity)
        
        # Get all images for this identity
        image_files = [f for f in os.listdir(identity_dir) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        
        if not image_files:
            print(f"Warning: No images found for {identity}")
            continue
        
        # Extract embeddings for all images
        embeddings = []
        for img_file in image_files:
            img_path = os.path.join(identity_dir, img_file)
            embedding = extract_embedding(model, img_path, device)
            if embedding is not None:
                embeddings.append(embedding)
                
                # Apply augmentation if specified
                if augment_ratio > 0 and random.random() < augment_ratio:
                    try:
                        # Load original image as numpy array for augmentation
                        img = cv2.imread(img_path)
                        if img is not None:
                            # Generate augmented versions
                            augmented_images = augment_face_image(img, augs_per_image)
                            
                            # Extract embeddings from augmented images
                            for aug_img in augmented_images:
                                # Convert numpy array to PIL Image
                                aug_pil = Image.fromarray(cv2.cvtColor(aug_img, cv2.COLOR_BGR2GRAY))
                                
                                # Transform and extract embedding
                                aug_tensor = transform(aug_pil).unsqueeze(0).to(device)
                                with torch.no_grad():
                                    _, aug_embedding = model(aug_tensor)
                                    aug_embedding = aug_embedding.cpu().squeeze().numpy()
                                    embeddings.append(aug_embedding)
                    except Exception as e:
                        print(f"Warning: Failed to augment {img_path}: {e}")
                        continue
        
        if not embeddings:
            print(f"Warning: No valid embeddings extracted for {identity}")
            continue
        
        # Average embeddings to get a single representation
        avg_embedding = np.mean(embeddings, axis=0)
        gallery[identity] = avg_embedding
    
    print(f"Gallery created with {len(gallery)} identities")
    
    # Save gallery
    torch.save(gallery, output_path)
    print(f"Gallery saved to {output_path}")
    return gallery

def update_gallery(model_path, gallery_path, new_data_dir, output_path=None, augment_ratio=0.5, augs_per_image=4):
    """Update an existing gallery with new identities"""
    if output_path is None:
        output_path = gallery_path
        
    # Load existing gallery
    existing_gallery = {}
    if os.path.exists(gallery_path):
        try:
            gallery_data = torch.load(gallery_path)
            
            # Handle both the old format (dict of embeddings) and new format (separate lists)
            if isinstance(gallery_data, dict) and "identities" in gallery_data:
                identities = gallery_data["identities"]
                embeddings = gallery_data["embeddings"]
                for i, identity in enumerate(identities):
                    existing_gallery[identity] = embeddings[i]
            else:
                existing_gallery = gallery_data
                
            print(f"Loaded existing gallery with {len(existing_gallery)} identities")
        except Exception as e:
            print(f"Error loading existing gallery: {e}")
            existing_gallery = {}
    else:
        print("No existing gallery found, creating new one")
    
    # Load model
    model, device = load_model(model_path)
    
    # Process new identities
    identities = [d for d in os.listdir(new_data_dir) if os.path.isdir(os.path.join(new_data_dir, d))]
    print(f"Found {len(identities)} new identities to process")
    
    # Create updated gallery
    updated_gallery = existing_gallery.copy()
    
    for identity in tqdm(identities, desc="Processing new identities"):
        identity_dir = os.path.join(new_data_dir, identity)
        
        # Get all images for this identity
        image_files = [f for f in os.listdir(identity_dir) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        
        if not image_files:
            print(f"Warning: No images found for {identity}")
            continue
        
        # Extract embeddings for all images
        embeddings = []
        for img_file in image_files:
            img_path = os.path.join(identity_dir, img_file)
            embedding = extract_embedding(model, img_path, device)
            if embedding is not None:
                embeddings.append(embedding)
                
                # Apply augmentation if specified
                if augment_ratio > 0 and random.random() < augment_ratio:
                    try:
                        # Load original image as numpy array for augmentation
                        img = cv2.imread(img_path)
                        if img is not None:
                            # Generate augmented versions
                            augmented_images = augment_face_image(img, augs_per_image)
                            
                            # Extract embeddings from augmented images
                            for aug_img in augmented_images:
                                # Convert numpy array to PIL Image
                                aug_pil = Image.fromarray(cv2.cvtColor(aug_img, cv2.COLOR_BGR2GRAY))
                                
                                # Transform and extract embedding
                                aug_tensor = transform(aug_pil).unsqueeze(0).to(device)
                                with torch.no_grad():
                                    _, aug_embedding = model(aug_tensor)
                                    aug_embedding = aug_embedding.cpu().squeeze().numpy()
                                    embeddings.append(aug_embedding)
                    except Exception as e:
                        print(f"Warning: Failed to augment {img_path}: {e}")
                        continue
        
        if not embeddings:
            print(f"Warning: No valid embeddings extracted for {identity}")
            continue
        
        # Average embeddings to get a single representation
        avg_embedding = np.mean(embeddings, axis=0)
        updated_gallery[identity] = avg_embedding
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save updated gallery with identities and embeddings separately
    serializable_gallery = {
        "identities": list(updated_gallery.keys()),
        "embeddings": [updated_gallery[identity] for identity in updated_gallery.keys()]
    }
    
    # Save updated gallery
    torch.save(serializable_gallery, output_path)
    print(f"Updated gallery saved to {output_path}")
    print(f"Gallery now contains {len(updated_gallery)} identities")
    return updated_gallery

def create_gallery_from_embeddings(gallery_path, embeddings_dict):
    """Create a gallery from a dictionary of embeddings"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(gallery_path), exist_ok=True)
        
        # Save embeddings dictionary directly
        torch.save(embeddings_dict, gallery_path)
        print(f"Gallery created at {gallery_path} with {len(embeddings_dict)} identities")
        return embeddings_dict
    except Exception as e:
        print(f"Error creating gallery from embeddings: {e}")
        return None

def update_gallery_from_embeddings(gallery_path, new_embeddings_dict):
    """Update an existing gallery with new embeddings"""
    try:
        # Load existing gallery if it exists
        existing_gallery = {}
        if os.path.exists(gallery_path):
            try:
                gallery_data = torch.load(gallery_path)
                
                # Handle both the old format (dict of embeddings) and new format (separate lists)
                if isinstance(gallery_data, dict) and "identities" in gallery_data:
                    identities = gallery_data["identities"]
                    embeddings = gallery_data["embeddings"]
                    for i, identity in enumerate(identities):
                        existing_gallery[identity] = embeddings[i]
                else:
                    existing_gallery = gallery_data
                    
                print(f"Loaded existing gallery with {len(existing_gallery)} identities")
            except Exception as e:
                print(f"Error loading existing gallery: {e}")
                existing_gallery = {}
        else:
            print("No existing gallery found, creating new one")
        
        # Merge with new embeddings
        updated_gallery = existing_gallery.copy()
        updated_gallery.update(new_embeddings_dict)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(gallery_path), exist_ok=True)
        
        # Save updated gallery
        torch.save(updated_gallery, gallery_path)
        print(f"Updated gallery saved to {gallery_path}")
        print(f"Gallery now contains {len(updated_gallery)} identities")
        return updated_gallery
        
    except Exception as e:
        print(f"Error updating gallery from embeddings: {e}")
        return None
