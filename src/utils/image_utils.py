import random
import albumentations as A

def create_face_augmentations():
    """Create a set of specific augmentations for face images"""
    augmentations = [
        # Brightness and Contrast Adjustment
        A.RandomBrightnessContrast(p=1.0, brightness_limit=(-0.2, 0.2), contrast_limit=(-0.2, 0.2)),
        
        # Gaussian Blur
        A.GaussianBlur(p=1.0, blur_limit=(3, 7)),
        
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

    # Mandatory augmentations
    mandatory_augmentations = [
        A.Compose([
            A.Resize(height=32, width=32),
            A.Resize(height=128, width=128)
        ]),
        A.Compose([
            A.Resize(height=24, width=24),
            A.Resize(height=128, width=128)
        ])
    ]

    # Apply mandatory augmentations
    for aug in mandatory_augmentations:
        augmented = aug(image=image)
        augmented_images.append(augmented['image'])

    # Always apply one random augmentation from the defined two
    rand_aug = random.choice(augmentations_list)
    aug_pipeline = A.Compose([rand_aug])
    augmented = aug_pipeline(image=image)
    augmented_images.append(augmented['image'])

    # Always apply one mix/double augmentation: randomly combine two augmentations from the four (mandatory + defined)
    all_augs = mandatory_augmentations + augmentations_list
    mix_choices = random.sample(all_augs, 2)
    # Compose them sequentially
    if isinstance(mix_choices[0], A.Compose) and isinstance(mix_choices[1], A.Compose):
        # Flatten the transforms
        transforms_seq = mix_choices[0].transforms + mix_choices[1].transforms
        mix_aug = A.Compose(transforms_seq)
    else:
        # If not both Compose, wrap each in Compose
        transforms_seq = []
        for aug in mix_choices:
            if isinstance(aug, A.Compose):
                transforms_seq += aug.transforms
            else:
                transforms_seq.append(aug)
        mix_aug = A.Compose(transforms_seq)
    augmented = mix_aug(image=image)
    augmented_images.append(augmented['image'])

    # Ensure exactly 4 images (pad with original if needed)
    while len(augmented_images) < 4:
        augmented_images.append(image)
    # If more than 4, trim
    augmented_images = augmented_images[:4]

    return augmented_images
