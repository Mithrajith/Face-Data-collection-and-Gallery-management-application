import random
import albumentations as A

def create_face_augmentations():
    """Create a set of specific augmentations for face images"""
    augmentations = [
        # Downscaling and Upscaling
        A.Compose([
            A.Resize(height=32, width=32),  # Downscale to low resolution
            A.Resize(height=128, width=128)  # Upscale back to original size
        ]),
        A.Compose([
            A.Resize(height=24, width=24),  # Downscale to low resolution
            A.Resize(height=128, width=128)  # Upscale back to original size
        ]),
        
        # Brightness and Contrast Adjustment
        A.RandomBrightnessContrast(p=1.0, brightness_limit=(-0.2, 0.2), contrast_limit=(-0.2, 0.2)),
        
        # Gaussian Blur
        A.GaussianBlur(p=1.0, blur_limit=(3, 7)),
        
        # Combined: Downscale + Blur
        A.Compose([
            A.Resize(height=48, width=48),
            A.Resize(height=128, width=128),
            A.GaussianBlur(p=1.0, blur_limit=(2, 5))
        ]),
        A.Compose([
            A.Resize(height=32, width=32),
            A.Resize(height=128, width=128),
            A.GaussianBlur(p=1.0, blur_limit=(2, 5))
        ]),
    ]
    return augmentations

def augment_face_image(image, num_augmentations=3):
    """
    Generate augmented versions of a face image in-memory
    
    This function applies a specific augmentation strategy:
    1. Always applies both downscale-upscale augmentations (32x32 and 24x24)
    2. Applies one additional random augmentation from the remaining list
    
    Args:
        image: Original face image (numpy array)
        num_augmentations: Number of augmented versions to generate (default 3)
    
    Returns:
        List of augmented images (numpy arrays)
    """
    augmentations_list = create_face_augmentations()
    augmented_images = []
    
    # Define the two specific downscale-upscale augmentations that should always be applied
    mandatory_augmentations = [
        # 32x32 downscale-upscale (index 0)
        A.Compose([
            A.Resize(height=32, width=32),
            A.Resize(height=128, width=128)
        ]),
        # 24x24 downscale-upscale (index 1)
        A.Compose([
            A.Resize(height=24, width=24),
            A.Resize(height=128, width=128)
        ])
    ]
    
    # Apply the two mandatory downscale-upscale augmentations
    for aug in mandatory_augmentations:
        augmented = aug(image=image)
        augmented_images.append(augmented['image'])
    
    # Apply additional random augmentations from the remaining list
    # Exclude the first two augmentations (the downscale-upscale ones)
    remaining_augmentations = augmentations_list[2:]  # Skip the first two
    
    additional_augs_needed = max(0, num_augmentations - 2)  # We already applied 2
    for i in range(additional_augs_needed):
        # Select random augmentation from remaining list
        selected_aug = random.choice(remaining_augmentations)
        
        # Apply augmentation
        if isinstance(selected_aug, A.Compose):
            augmented = selected_aug(image=image)
        else:
            aug_pipeline = A.Compose([selected_aug])
            augmented = aug_pipeline(image=image)
        
        augmented_images.append(augmented['image'])
    
    return augmented_images
