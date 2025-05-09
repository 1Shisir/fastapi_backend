from fastapi import APIRouter,Depends,HTTPException,status,File,UploadFile,Form
import time
import logging,json
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from app.db.models.user import User
from app.db.models.post import Post
from app.db.models.like import Like
from app.db.models.user_info import UserInfo
from app.schemas.user import UserOut,ConnectionRequestWithUser
from app.schemas.user_info import UserInfoCreate, UserInfoResponse, UserInfoUpdate
from app.db.session import get_db
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.security import get_current_user,are_friends
from cloudinary import uploader
from cloudinary.uploader import upload,destroy
from cloudinary.exceptions import Error as CloudinaryError
from app.db.models.connection_request import ConnectionRequest
from app.schemas.post import PostOut


router = APIRouter()

#get user who are  not friends with the current user
# @router.get("/suggested",response_model=List[UserOut])
# def get_users(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     users = db.query(User,UserInfo)\
#         .outerjoin(UserInfo, User.id == UserInfo.user_id)\
#         .filter(
#             User.role != "admin",
#             User.id != current_user.id,
#         )\
#         .all()
    
#     if not users:
#         return []  # Return an empty list if no users are found

#     #formatting the response
#     response = [
#         {
#             "id": user.id,
#             "email": user.email,
#             "first_name": user.first_name,
#             "last_name": user.last_name,
#             "role": user.role,
#             "profile_picture": user_info.profile_picture
#         }
#         for user,user_info in users
#         if not are_friends(db, current_user.id, user.id)
#     ]
#     return response    


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
@router.post("/me/add-bio", response_model=UserInfoResponse)
async def add_bio(
    bio: str = Form(...),
    profile_picture: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Validate and parse the JSON string
        parsed_bio = json.loads(bio)

        user_info = UserInfoCreate(**parsed_bio)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JSON format for bio"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    existing_info = db.query(UserInfo).filter(
        UserInfo.user_id == current_user.id
    ).first()

    profile_data = {}
    if profile_picture and profile_picture.filename and profile_picture.size > 0:
        try:
            # Verify file is actually received
            if not profile_picture.filename:
                raise HTTPException(400, "No file provided")
            
            # Validate file type
            if profile_picture.content_type not in ["image/jpeg", "image/png", "image/webp"]:
                raise HTTPException(400, "Invalid image format")

            # Validate file size
            if profile_picture.size > 5 * 1024 * 1024:
                raise HTTPException(400, "File too large (max 5MB)")

            # Reset file pointer to ensure full read
            await profile_picture.seek(0)

            # Actual upload
            upload_result = uploader.upload(
                await profile_picture.read(),
                folder="profile_pics",
                public_id=f"user_{current_user.id}_{int(time.time())}",
                resource_type="image",
                overwrite=True,
                quality="auto:good"  # Optimize image
            )
            
            profile_data = {
                "profile_picture": upload_result["secure_url"],
                "profile_public_id": upload_result["public_id"]
            }

        except CloudinaryError as e:
            logging.error(f"Cloudinary Error: {str(e)}")
            raise HTTPException(500, f"Cloud upload failed: {e}")
        except Exception as e:
            logging.error(f"Unexpected Error: {str(e)}", exc_info=True)
            raise HTTPException(500, "Image processing failed")

    try:
        if existing_info:
            # Delete old image if exists and new image uploaded
            if profile_data and existing_info.profile_public_id:
                try:
                    uploader.destroy(existing_info.profile_public_id)
                except CloudinaryError as e:
                    logging.error(f"Cloudinary delete error: {str(e)}")

            # Update fields
            for field, value in user_info.dict().items():
                setattr(existing_info, field, value)
            
            if profile_data:
                existing_info.profile_picture = profile_data["profile_picture"]
                existing_info.profile_public_id = profile_data["profile_public_id"]
            
            db.commit()
            db.refresh(existing_info)
            return existing_info
        else:
            new_info = UserInfo(
                user_id=current_user.id,
                **user_info.dict(),
                **profile_data
            )
            db.add(new_info)
            db.commit()
            db.refresh(new_info)
            return new_info

    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error: {str(e)}")
        # Cleanup uploaded image if database operation failed
        if profile_data.get("profile_public_id"):
            try:
                uploader.destroy(profile_data["profile_public_id"])
            except CloudinaryError as ce:
                logging.error(f"Cloudinary cleanup error: {str(ce)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save profile information"
        )    
        return new_info

#update user bio

@router.patch("/me/update-bio", response_model=UserInfoResponse)
async def update_user_bio(
    bio: Optional[str] = Form(default=None),
    profile_picture: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Parse and validate the bio JSON with UserInfoUpdate schema
        parsed_bio = json.loads(bio)
        user_info = UserInfoUpdate(**parsed_bio)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JSON format for bio"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    existing_info = db.query(UserInfo).filter(
        UserInfo.user_id == current_user.id
    ).first()

    profile_data = {}
    if profile_picture:
        try:
            # Validate file type and size
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
        if existing_info:
            # Update existing UserInfo with provided fields only
            update_data = user_info.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(existing_info, field, value)

            # Handle profile picture update
            if profile_data:
                # Delete old image if exists
                if existing_info.profile_public_id:
                    try:
                        uploader.destroy(existing_info.profile_public_id)
                    except CloudinaryError as e:
                        logging.error(f"Failed to delete old image: {str(e)}")
                existing_info.profile_picture = profile_data["profile_picture"]
                existing_info.profile_public_id = profile_data["profile_public_id"]

            db.commit()
            db.refresh(existing_info)
            return existing_info
        else:
            # Create new UserInfo with provided fields and profile data
            new_info_data = user_info.dict(exclude_unset=True)
            new_info = UserInfo(
                user_id=current_user.id,
                **new_info_data,
                **profile_data
            )
            db.add(new_info)
            db.commit()
            db.refresh(new_info)
            return new_info
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error: {str(e)}")
        # Cleanup uploaded image on failure
        if profile_data.get("profile_public_id"):
            try:
                uploader.destroy(profile_data["profile_public_id"])
            except CloudinaryError as ce:
                logging.error(f"Cloudinary cleanup error: {str(ce)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save profile information"
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
