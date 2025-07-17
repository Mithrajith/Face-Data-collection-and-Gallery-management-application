# Compatibility shim for gallery_manager imports
# Functions have been moved to ml.gallery_operations and ml.embeddings

from ml.gallery_operations import (
    create_gallery,
    update_gallery,
    create_gallery_from_embeddings,
    update_gallery_from_embeddings
)

from ml.embeddings import (
    load_model,
    extract_embedding
)

from utils.image_utils import (
    create_face_augmentations,
    augment_face_image
)
