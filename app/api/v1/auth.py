from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from app.db.models.user import User
from app.db.models.user_info import UserInfo
from app.db.models.notifications import Notification
from app.schemas.user import *
from app.schemas.token import Token
from app.core.security import hash_password, verify_password, create_access_token
from app.db.session import get_db


router = APIRouter()


@router.post("/register") 
def register(user_in: UserBase, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(
        email= user_in.email,
        first_name= user_in.first_name,
        last_name= user_in.last_name,
        password=hash_password(user_in.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create UserInfo entry
    user_info = UserInfo(
        user_id=new_user.id
    )
     
   
    db.add(user_info)
    db.commit()
    db.refresh(user_info)

    admins = db.query(User).filter(User.role == "admin").all()
    for admin in admins:
        notification = Notification(
            user_id=admin.id,
            message=f"New user registered: {new_user.email}",
            type="new_user",
            related_user_id=new_user.id
        )
        db.add(notification)
    db.commit()

    return {"msg": "User registered successfully"}

@router.post("/login", response_model=Token,)
async def login( db: Session = Depends(get_db),form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).options(joinedload(User.user_info)).filter(User.email == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    token_data = {
        "sub": user.email,
        "role": user.role,
    }

    #check of admin
    if user.role == "admin":
        access_token = create_access_token(
            token_data
        )
        return Token(access_token=access_token, token_type="bearer", role=user.role)
    
    # Regular users need verified UserInfo
    if not user.user_info or not user.user_info.is_verified == True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not verified. Please wait for verification from admin."
        )        

    access_token = create_access_token(
        token_data
    )
    return Token(access_token=access_token, token_type="bearer", role=user.role, user_id=user.id)
    
   