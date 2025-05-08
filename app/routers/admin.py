from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.notifications import Notification
from app.db.models.user_info import UserInfo
from app.schemas.user import UserOut, UnverifiedUserInfoResponse
from app.core.security import get_current_admin
from typing import List


router = APIRouter()

@router.get("/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    return {"msg": "Welcome to the admin dashboard"}


#get all users except admin
@router.get("/users", response_model=List[UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    users = db.query(User,UserInfo)\
        .outerjoin(UserInfo, User.id == UserInfo.user_id)\
        .filter(
            User.role != "admin",
            UserInfo.is_verified == True
        )\
        .all()
    if not users:
        return []  # Return an empty list if no users are found
    #formatting the response
    response = [
        {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "profile_picture": user_info.profile_picture
        }
        for user,user_info in users
    ]
    return response



#get all unverified users
@router.get("/unverified-users", response_model=List[UnverifiedUserInfoResponse])
def get_unverified_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    unverified_users = db.query(User, UserInfo)\
        .outerjoin(UserInfo, User.id == UserInfo.user_id)\
        .filter(
            User.role != "admin",
            UserInfo.is_verified == False
        )\
        .all()

    if not unverified_users:
        return []  # Return an empty list if no unverified users are found
    
    #formatting the response
    response = [
        {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "profile_picture": user_info.profile_picture if user_info else None,
            "is_verified": user_info.is_verified if user_info else False
        }
        for user,user_info  in unverified_users
    ]
    return response




#verify user
@router.post("/verify/{user_id}")
def verify_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    # First check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Now check user info
    user_info = db.query(UserInfo).filter(UserInfo.user_id == user_id).first()
    
    # This should never happen if registration is correct, but just in case
    if not user_info:
        user_info = UserInfo(user_id=user_id, is_verified=True)
        db.add(user_info)
    else:
        user_info.is_verified = True
    
    db.commit()
    db.refresh(user_info)


    #notify user about verification
    notification = Notification(
        user_id=user.id,
        message="Your account has been verified",
        type="account verification",
        related_user_id=user.id
    )
    db.add(notification)
    db.commit()

    return {"msg": "User verified successfully"}    