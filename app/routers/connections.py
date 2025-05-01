from fastapi import APIRouter, Depends, HTTPException, status,WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.notifications import Notification
from app.db.models.connection_request import ConnectionRequest
from app.core.security import get_current_user, get_websocket_user
from app.schemas.notifications import NotificationBase, NotificationResponse
from app.schemas.connection_request import FriendResponse
import asyncio

router = APIRouter()

# Send connection request
@router.post("/request/{receiver_id}")
async def send_connection_request(
    receiver_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if receiver exists
    receiver = db.query(User).get(receiver_id)
    if not receiver:
        raise HTTPException(status_code=404, detail="User not found")

    # Check for existing request
    existing = db.query(ConnectionRequest).filter(
        ConnectionRequest.sender_id == current_user.id,
        ConnectionRequest.receiver_id == receiver_id,
        ConnectionRequest.status == "pending"
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Request already sent")

    # Create new request
    new_request = ConnectionRequest(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        status="pending"
    )
    
    # Create notification
    notification = Notification(
        user_id=receiver_id,
        message=f"{current_user.email} wants to connect with you",
        type="connection_request",
        related_request_id=new_request.id
    )

    db.add(new_request)
    db.add(notification)
    db.commit()
    
    return {"message": "Connection request sent"}

# Accept connection request
@router.put("/accept/{request_id}")
async def accept_connection_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    request = db.query(ConnectionRequest).get(request_id)
    
    if not request or request.receiver_id != current_user.id:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.status != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")

    request.status = "accepted"
    
    # Create notifications
    sender_notification = Notification(
        user_id=request.sender_id,
        message=f"{current_user.email} accepted your connection request",
        type="request_accepted"
    )
    
    db.add(sender_notification)
    db.commit()
    
    return {"message": "Request accepted"}

# Get notifications
@router.get("/notifications", response_model=List[NotificationBase])
async def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Notification)\
        .filter(Notification.user_id == current_user.id)\
        .order_by(Notification.created_at.desc())\
        .all()


# Mark notification as read
@router.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notification = db.query(Notification)\
        .filter(Notification.id == notification_id,
                Notification.user_id == current_user.id)\
        .first()
    
    if notification:
        notification.is_read = True
        db.commit()
    
    return {"status": "marked as read"}

      
# WebSocket for real-time notifications
@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(get_db)
):
    await websocket.accept()
    user = await get_websocket_user(token, db)
    
    try:
        while True:
            notifications = db.query(Notification)\
                .options(joinedload(Notification.related_user))\
                .filter(
                    Notification.user_id == user.id,
                    Notification.is_read == False
                )\
                .all()

            if notifications:
                await websocket.send_json([
                    {
                        "id": n.id,
                        "message": n.message,
                        "type": n.type,
                        "created_at": n.created_at.isoformat(),
                        "related_user": {
                            "id": n.related_user.id,
                            "email": n.related_user.email
                        } if n.related_user else None
                    }
                    for n in notifications
                ])
            
            await asyncio.sleep(60) # Check every 60 seconds
    
    except WebSocketDisconnect:
        pass

@router.get("/friends")
def get_friends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get all accepted connections
    connections = db.query(ConnectionRequest)\
        .options(
            joinedload(ConnectionRequest.sender).joinedload(User.user_info),
            joinedload(ConnectionRequest.receiver).joinedload(User.user_info)
        )\
        .filter(
            ((ConnectionRequest.sender_id == current_user.id) |
             (ConnectionRequest.receiver_id == current_user.id)) &
            (ConnectionRequest.status == "accepted")
        )\
        .all()

    friends  = []  
    seen_ids = set()

    for conn in connections:
        # Determine which user is the friend
        friend = conn.receiver if conn.sender_id == current_user.id else conn.sender
        
        # Avoid duplicates
        if friend.id in seen_ids:
            continue
            
        seen_ids.add(friend.id)

        friends.append({
            "email": friend.email,
            "first_name": friend.first_name,
            "last_name": friend.last_name,
            "profile_picture": friend.user_info.profile_picture if friend.user_info else None,

        })
        

    return friends