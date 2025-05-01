from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.notifications import Notification
from app.db.models.user_info import UserInfo
from app.schemas.user import UserOut
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
    users = db.query(User).filter(User.role != "admin").all()
    if not users:
        raise HTTPException(status_code=404, detail="No users found")
    return users

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