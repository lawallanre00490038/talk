# app/api/routers/users.py
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
import uuid
from app.core.cloudinary import cloudinary
import cloudinary.api
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.db.models import User
from app.schemas.auth import TokenUser, UserPublic
from app.db.repositories.user_repo import user_repo
from urllib.parse import quote

router = APIRouter()

@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: TokenUser = Depends(get_current_user_dependency(settings=settings))):
    """
    Get current user's profile.
    """
    return current_user

@router.get("/{user_id}", response_model=UserPublic)
async def read_user_by_id(
    user_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Get a specific user's public profile by ID.
    """
    user = await user_repo.get(session, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user



# ----------------------------
# Cloudinary categories (folders)
# ----------------------------
CLOUDINARY_CATEGORIES = [
    "campus_post", "lasu_post", "oau_post", "reels", "unilag_post", "yabatech_post", "chatbot"
]

# ----------------------------
# Get all files for a category
# ----------------------------
@router.get("/media-files/{category}", response_model=list[str])
async def get_media_files_by_category(category: str):
    """
    Return all media file URLs in a given category (subfolder).

    Args:
        category (str): The subfolder name inside media_files, e.g., 'campus_blog', 'lasu_blog', 'oau_post', 'reels', 'unilag_post', 'yabatech_post'.

    Returns:
        List[str]: List of file URLs under that category.
    """
    if category not in CLOUDINARY_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category '{category}'")

    try:
        resources = cloudinary.api.resources(
            type="upload",
            prefix=category,   # fetch all files under this folder
            max_results=500,  # adjust based on expected number of files
            context=True
        )
        urls = [res.get("secure_url") for res in resources.get("resources", [])]

    except cloudinary.exceptions.Error as e:
        raise HTTPException(status_code=500, detail=f"Cloudinary error: {str(e)}")

    return urls