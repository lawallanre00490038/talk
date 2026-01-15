import os
import mimetypes
from app.core.cloudinary import cloudinary
import cloudinary.uploader

# Base folder where your media files are stored
MEDIA_BASE_FOLDER = "media_files"

# List of allowed categories/folders
CATEGORIES = [
    "campus_post",
    "lasu_post",
    "reels",
]

def upload_file(file_path: str, folder: str):
    """
    Uploads a single file (image or video) to Cloudinary in the given folder.
    Returns the secure URL if successful, else None.
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    resource_type = "video" if mime_type and mime_type.startswith("video") else "image"

    public_id = os.path.splitext(os.path.basename(file_path))[0]  # filename without extension

    try:
        result = cloudinary.uploader.upload(
            file_path,
            folder=folder,
            public_id=public_id,
            resource_type=resource_type,
            overwrite=True
        )
        print(f"✅ Uploaded: {file_path} → {result.get('secure_url')}")
        return result.get("secure_url")
    except Exception as e:
        print(f"❌ Failed to upload {file_path}: {e}")
        return None


def upload_media_folder():
    """
    Walk through MEDIA_BASE_FOLDER and upload all files under valid categories.
    """
    for category in CATEGORIES:
        category_path = os.path.join(MEDIA_BASE_FOLDER, category)
        if not os.path.exists(category_path):
            print(f"⚠️ Category folder not found: {category_path}")
            continue

        for root, _, files in os.walk(category_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                upload_file(file_path, folder=category)


if __name__ == "__main__":
    upload_media_folder()
