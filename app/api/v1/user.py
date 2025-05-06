from fastapi import APIRouter,Depends,HTTPException,status,File,UploadFile,Form
from fastapi.encoders import jsonable_encoder
import time
import logging,json
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from app.db.models.user import User
from app.db.models.user_info import UserInfo
from app.schemas.user import *
from app.schemas.user_info import UserInfoCreate, UserInfoResponse
from app.db.session import get_db
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from cloudinary import uploader
from cloudinary.uploader import upload,destroy
from cloudinary.exceptions import Error as CloudinaryError


router = APIRouter()

@router.get("/",response_model=List[UserOut])
def get_users(
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.role != "admin").all()
    return user


#Add user bio
@router.post("/me/add-bio", response_model=UserInfoResponse)
async def add_bio(
    bio: str = Form(...),
    profile_picture: Optional[UploadFile] = File(None),
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
    if profile_picture:
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
               

# Get user bio
@router.get("/me/bio", response_model=UserInfoResponse)
def get_user_bio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_info = db.query(UserInfo).filter(
        UserInfo.user_id == current_user.id
    ).first()

    if not user_info:
        raise HTTPException(status_code=404, detail="User bio not found")

    return user_info        