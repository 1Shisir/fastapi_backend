from fastapi import APIRouter,Depends,HTTPException,status,File,UploadFile,Body
import time
import logging
from sqlalchemy.exc import SQLAlchemyError
from app.db.models.user import User
from app.db.models.post import Post
from app.db.models.like import Like
from app.db.models.user_info import UserInfo
from app.schemas.user import UserOut,ConnectionRequestWithUser
from app.schemas.user_info import UserInfoResponse, UserInfoUpdate
from app.db.session import get_db
from typing import List
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from cloudinary import uploader
from cloudinary.exceptions import Error as CloudinaryError
from app.db.models.connection_request import ConnectionRequest
from app.schemas.post import PostOut


router = APIRouter()

#get user who are  not friends with the current user
# This endpoint fetches a list of users who are not friends with the current user.
# It excludes users who have sent connection requests to the current user.
@router.get("/suggested", response_model=List[UserOut])
def get_suggested_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Subquery to find all users with existing connection requests
    connection_subquery = (
        db.query(ConnectionRequest.sender_id.label("user_id"))
        .filter(ConnectionRequest.receiver_id == current_user.id)
        .union_all(
            db.query(ConnectionRequest.receiver_id.label("user_id"))
            .filter(ConnectionRequest.sender_id == current_user.id)
        )
        .subquery()
    )

    # Main query
    suggested_users = (
        db.query(User, UserInfo)
        .outerjoin(UserInfo, User.id == UserInfo.user_id)
        .filter(
            User.role != "admin",
            User.id != current_user.id,
            ~User.id.in_(db.query(connection_subquery.c.user_id))
        )
        .all()
    )

    return [
        {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "profile_picture": user_info.profile_picture if user_info else None
        }
        for user, user_info in suggested_users
    ]


# Get user details
# This endpoint fetches the current user's details, including their profile picture if available.
@router.get("/me", response_model=UserOut)
def get_user_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Fetch user and user info
    # Use outerjoin to include user info even if it doesn't exist
    result = db.query(User, UserInfo)\
        .outerjoin(UserInfo, User.id == UserInfo.user_id)\
        .filter(User.id == current_user.id)\
        .first()

    user, user_info = result if result else (current_user, None)

    # Build response dictionary
    response = {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role,
        "profile_picture": user_info.profile_picture if user_info else None
    }

    return response

#Add user bio
# This endpoint allows the user to update their bio information.

@router.put("/me/update-bio", response_model=UserInfoResponse)
async def update_bio(
    user_info_update: UserInfoUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        user_info = db.query(UserInfo).filter(
            UserInfo.user_id == current_user.id
        ).first()

        update_data = user_info_update.dict(exclude_unset=True)
        old_public_id = None

        if user_info:
            # Store old public ID before changes
            old_public_id = user_info.profile_public_id

            # Update fields
            for key, value in update_data.items():
                setattr(user_info, key, value)

            # Handle profile picture removal
            if 'profile_picture' in update_data and update_data['profile_picture'] is None:
                user_info.profile_public_id = None
                if old_public_id:
                    try:
                        uploader.destroy(old_public_id)
                    except CloudinaryError as e:
                        logging.error(f"Cloudinary delete error: {str(e)}")
        else:
            # Create new entry
            user_info = UserInfo(
                user_id=current_user.id,
                **update_data
            )
            db.add(user_info)

        db.commit()
        db.refresh(user_info)
        return user_info

    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update bio information"
        )
    


#add user profile picture
@router.put("/me/add-profile-picture", response_model=UserInfoResponse)
async def update_profile_picture(
    profile_picture: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing_info = db.query(UserInfo).filter(
        UserInfo.user_id == current_user.id
    ).first()

    profile_data = {}
    try:
        # Validate file
        if not profile_picture.filename:
            raise HTTPException(400, "No file provided")
        
        if profile_picture.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(400, "Invalid image format")

        if profile_picture.size > 5 * 1024 * 1024:
            raise HTTPException(400, "File too large (max 5MB)")

        await profile_picture.seek(0)
        upload_result = uploader.upload(
            await profile_picture.read(),
            folder="profile_pics",
            public_id=f"user_{current_user.id}_{int(time.time())}",
            resource_type="image",
            overwrite=True,
            quality="auto:good"
        )
        
        profile_data = {
            "profile_picture": upload_result["secure_url"],
            "profile_public_id": upload_result["public_id"]
        }

    except CloudinaryError as e:
        logging.error(f"Cloudinary Error: {str(e)}")
        raise HTTPException(500, f"Image upload failed: {e}")
    except Exception as e:
        logging.error(f"Unexpected Error: {str(e)}", exc_info=True)
        raise HTTPException(500, "Image processing failed")

    try:
        # Delete old image if exists
        old_public_id = None
        if existing_info:
            old_public_id = existing_info.profile_public_id
            existing_info.profile_picture = profile_data["profile_picture"]
            existing_info.profile_public_id = profile_data["profile_public_id"]
        else:
            existing_info = UserInfo(
                user_id=current_user.id,
                **profile_data
            )
            db.add(existing_info)
        
        db.commit()
        db.refresh(existing_info)

        # Delete old image after successful update
        if old_public_id:
            try:
                uploader.destroy(old_public_id)
            except CloudinaryError as e:
                logging.error(f"Failed to delete old image: {str(e)}")

        return existing_info

    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error: {str(e)}")
        if profile_data.get("profile_public_id"):
            try:
                uploader.destroy(profile_data["profile_public_id"])
            except CloudinaryError as ce:
                logging.error(f"Cloudinary cleanup error: {str(ce)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save profile picture"
        )


               

# Get user bio
@router.get("/me/bio", response_model=UserInfoResponse)
def get_user_bio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_info = db.query(UserInfo).filter(
        UserInfo.user_id == current_user.id,
        UserInfo.profile_public_id != None
    ).first()

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User bio not found"
        )

    return user_info


# get requests sent by other users to the current user
@router.get("/me/requests", response_model=List[ConnectionRequestWithUser])
def get_connection_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get all pending requests sent to current user
    requests = db.query(User, ConnectionRequest, UserInfo)\
        .join(ConnectionRequest, User.id == ConnectionRequest.sender_id)\
        .outerjoin(UserInfo, User.id == UserInfo.user_id)\
        .filter(
            ConnectionRequest.receiver_id == current_user.id,
            ConnectionRequest.status == "pending",
            User.role != "admin",
            User.id != current_user.id
        )\
        .all()

    # Format response with profile pictures
    response = [
        {
            "request_id": connection_request.id,
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "profile_picture": user_info.profile_picture if user_info else None
        }
        for user, connection_request, user_info in requests 
    ]

    return response

#get posts liked by the current user
@router.get("/me/liked-posts", response_model=List[PostOut])
def get_liked_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Fetch posts liked by the current user
    liked_posts = db.query(Post)\
        .join(Like, Post.id == Like.post_id)\
        .filter(
            Like.user_id == current_user.id
        )\
        .all()
    
    if not liked_posts:
        return []  # Return an empty list if no liked posts are found
    
    return liked_posts

# check user verification status
@router.get("/status/{user_id}", status_code=status.HTTP_200_OK)
def check_user_status(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_info = db.query(UserInfo).filter(UserInfo.user_id == user_id).first()
    if not user_info:
        raise HTTPException(status_code=404, detail="User info not found")
    
    if not user_info.is_verified:
        raise HTTPException(status_code=404, detail="User not verified! Please wait for admin approval.")

    return {
        "is_verified": user_info.is_verified,
        "user_id": user.id,
        "username": f"{user.first_name} {user.last_name}",
    }
   
