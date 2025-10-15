"""Avatar management API endpoints."""

import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image

from kohakuhub.db import Organization, User
from kohakuhub.db_operations import get_organization, get_user_by_username
from kohakuhub.logger import get_logger
from kohakuhub.auth.dependencies import get_current_user, get_optional_user

logger = get_logger("AVATAR")

router = APIRouter()

# Avatar configuration
AVATAR_SIZE = 1024  # Output size (1024x1024)
AVATAR_MAX_INPUT_SIZE = 10 * 1024 * 1024  # 10MB max input
AVATAR_JPEG_QUALITY = 95
ALLOWED_MIME_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]


def process_avatar_image(image_bytes: bytes) -> bytes:
    """Process uploaded image: resize and center crop to 1024x1024 JPEG.

    Args:
        image_bytes: Raw image bytes

    Returns:
        Processed JPEG bytes

    Raises:
        HTTPException: If image processing fails
    """
    try:
        # Open image
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary (handles RGBA, P, etc.)
        if img.mode != "RGB":
            # Create white background for transparency
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA" or img.mode == "P":
                background.paste(
                    img, mask=img.split()[-1] if img.mode == "RGBA" else None
                )
            else:
                background.paste(img)
            img = background

        # Calculate dimensions for center crop to square
        width, height = img.size
        if width > height:
            # Landscape: crop width
            left = (width - height) // 2
            img = img.crop((left, 0, left + height, height))
        elif height > width:
            # Portrait: crop height
            top = (height - width) // 2
            img = img.crop((0, top, width, top + width))
        # else: already square, no crop needed

        # Resize to target size with high-quality resampling
        img = img.resize((AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)

        # Save as JPEG with specified quality
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=AVATAR_JPEG_QUALITY, optimize=True)
        output.seek(0)

        return output.read()

    except Exception as e:
        logger.error(f"Failed to process avatar image: {e}")
        raise HTTPException(
            400, detail="Failed to process image. Ensure it's a valid image file."
        )


# ===== User Avatar Endpoints =====


@router.post("/users/{username}/avatar")
async def upload_user_avatar(
    username: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Upload avatar for a user.

    Args:
        username: Username
        file: Image file (JPEG/PNG/WebP/GIF)
        user: Current authenticated user

    Returns:
        Success message

    Raises:
        HTTPException: If not authorized or invalid image
    """
    # Check authorization (user themselves or admin can upload)
    target_user = get_user_by_username(username)
    if not target_user:
        raise HTTPException(404, detail="User not found")

    # Only user themselves can upload (we'll add admin check later if needed)
    if user.id != target_user.id:
        raise HTTPException(403, detail="Not authorized to update this user's avatar")

    # Validate content type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            400,
            detail=f"Invalid image type. Allowed: JPEG, PNG, WebP, GIF",
        )

    # Read file
    content = await file.read()

    # Validate size
    if len(content) > AVATAR_MAX_INPUT_SIZE:
        raise HTTPException(
            400,
            detail=f"Image too large. Maximum: {AVATAR_MAX_INPUT_SIZE // 1024 // 1024}MB",
        )

    # Process image (resize, crop, convert to JPEG)
    try:
        processed_jpeg = process_avatar_image(content)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error processing avatar", e)
        raise HTTPException(500, detail="Failed to process avatar")

    # Update user avatar
    target_user.avatar = processed_jpeg
    target_user.avatar_updated_at = datetime.now(timezone.utc)
    target_user.save()

    logger.success(
        f"Avatar uploaded for user: {username} (size={len(processed_jpeg)} bytes)"
    )

    return {
        "success": True,
        "message": "Avatar uploaded successfully",
        "size_bytes": len(processed_jpeg),
    }


@router.get("/users/{username}/avatar")
async def get_user_avatar(
    username: str, _user: User | None = Depends(get_optional_user)
):
    """Get user avatar image.

    Args:
        username: Username
        _user: Optional authenticated user (for logging)

    Returns:
        JPEG image

    Raises:
        HTTPException: If user not found or no avatar
    """
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(404, detail="User not found")

    if not user.avatar:
        raise HTTPException(404, detail="No avatar set")

    # Return image with cache headers
    return Response(
        content=user.avatar,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=86400",  # 24 hour cache
            "Last-Modified": (
                user.avatar_updated_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
                if user.avatar_updated_at
                else ""
            ),
        },
    )


@router.delete("/users/{username}/avatar")
async def delete_user_avatar(
    username: str,
    user: User = Depends(get_current_user),
):
    """Delete user avatar.

    Args:
        username: Username
        user: Current authenticated user

    Returns:
        Success message
    """
    target_user = get_user_by_username(username)
    if not target_user:
        raise HTTPException(404, detail="User not found")

    if user.id != target_user.id:
        raise HTTPException(403, detail="Not authorized to delete this user's avatar")

    if not target_user.avatar:
        raise HTTPException(404, detail="No avatar to delete")

    target_user.avatar = None
    target_user.avatar_updated_at = None
    target_user.save()

    logger.success(f"Avatar deleted for user: {username}")

    return {"success": True, "message": "Avatar deleted successfully"}


# ===== Organization Avatar Endpoints =====


@router.post("/organizations/{org_name}/avatar")
async def upload_org_avatar(
    org_name: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Upload avatar for an organization.

    Args:
        org_name: Organization name
        file: Image file (JPEG/PNG/WebP/GIF)
        user: Current authenticated user

    Returns:
        Success message

    Raises:
        HTTPException: If not authorized or invalid image
    """
    from kohakuhub.db_operations import get_user_organization

    org = get_organization(org_name)
    if not org:
        raise HTTPException(404, detail="Organization not found")

    # Check if user is admin of the organization
    user_org = get_user_organization(user.id, org.id)
    if not user_org or user_org.role not in ["admin", "super-admin"]:
        raise HTTPException(403, detail="Not authorized to update organization avatar")

    # Validate content type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            400,
            detail=f"Invalid image type. Allowed: JPEG, PNG, WebP, GIF",
        )

    # Read file
    content = await file.read()

    # Validate size
    if len(content) > AVATAR_MAX_INPUT_SIZE:
        raise HTTPException(
            400,
            detail=f"Image too large. Maximum: {AVATAR_MAX_INPUT_SIZE // 1024 // 1024}MB",
        )

    # Process image
    try:
        processed_jpeg = process_avatar_image(content)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error processing avatar", e)
        raise HTTPException(500, detail="Failed to process avatar")

    # Update organization avatar
    org.avatar = processed_jpeg
    org.avatar_updated_at = datetime.now(timezone.utc)
    org.save()

    logger.success(
        f"Avatar uploaded for org: {org_name} (size={len(processed_jpeg)} bytes)"
    )

    return {
        "success": True,
        "message": "Avatar uploaded successfully",
        "size_bytes": len(processed_jpeg),
    }


@router.get("/organizations/{org_name}/avatar")
async def get_org_avatar(
    org_name: str, _user: User | None = Depends(get_optional_user)
):
    """Get organization avatar image.

    Args:
        org_name: Organization name
        _user: Optional authenticated user (for logging)

    Returns:
        JPEG image

    Raises:
        HTTPException: If organization not found or no avatar
    """
    org = get_organization(org_name)
    if not org:
        raise HTTPException(404, detail="Organization not found")

    if not org.avatar:
        raise HTTPException(404, detail="No avatar set")

    # Return image with cache headers
    return Response(
        content=org.avatar,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=86400",  # 24 hour cache
            "Last-Modified": (
                org.avatar_updated_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
                if org.avatar_updated_at
                else ""
            ),
        },
    )


@router.delete("/organizations/{org_name}/avatar")
async def delete_org_avatar(
    org_name: str,
    user: User = Depends(get_current_user),
):
    """Delete organization avatar.

    Args:
        org_name: Organization name
        user: Current authenticated user

    Returns:
        Success message
    """
    from kohakuhub.db_operations import get_user_organization

    org = get_organization(org_name)
    if not org:
        raise HTTPException(404, detail="Organization not found")

    user_org = get_user_organization(user.id, org.id)
    if not user_org or user_org.role not in ["admin", "super-admin"]:
        raise HTTPException(403, detail="Not authorized to delete organization avatar")

    if not org.avatar:
        raise HTTPException(404, detail="No avatar to delete")

    org.avatar = None
    org.avatar_updated_at = None
    org.save()

    logger.success(f"Avatar deleted for org: {org_name}")

    return {"success": True, "message": "Avatar deleted successfully"}
