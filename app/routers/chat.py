from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.sql import case
from collections import defaultdict
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.user_info import UserInfo
from app.db.models.group import Group,GroupMessage,group_user_association
from app.db.models.message import Message
from app.db.models.group import GroupMessage
from app.core.security import get_current_user,are_friends,get_websocket_user
from app.schemas.message import MessageBase


router = APIRouter()

active_connections = defaultdict(dict)

class ConnectionManager:
    def __init__(self):
        self.active_connections = defaultdict(dict)

    async def connect(self, websocket: WebSocket, user_id: int, friend_id: int):
        await websocket.accept()
        room_id = tuple(sorted([user_id, friend_id]))
        self.active_connections[room_id][user_id] = websocket

    def disconnect(self, user_id: int, friend_id: int):
        room_id = tuple(sorted([user_id, friend_id]))
        if user_id in self.active_connections[room_id]:
            del self.active_connections[room_id][user_id]
        if not self.active_connections[room_id]:
            del self.active_connections[room_id]


    async def send_personal_message(self, message: dict, user_id: int, friend_id: int):
        room_id = tuple(sorted([user_id, friend_id]))
        if connection := self.active_connections[room_id].get(friend_id):
            await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/chat/{friend_id}")
async def websocket_chat(
    websocket: WebSocket,
    friend_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    user = await get_websocket_user(token, db)
    if not user:
        await websocket.send_json({"error": "Invalid token"})
        await websocket.close(code=1008)
        return
    
    # Verify friendship
    if not are_friends(db, user.id, friend_id):
        await websocket.send_json({"error": "Not friends"})
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user.id, friend_id)
    
    try:
        while True:

            data = await websocket.receive_json()

            # Validate data
            if "message" not in data:
                await websocket.send_json({"error": "Invalid message format"})
                continue
            
            # Save message to database
            new_message = Message(
                sender_id=user.id,
                receiver_id=friend_id,
                content=data["message"],
                timestamp=datetime.utcnow()
            )
            db.add(new_message)
            db.commit()
            
            # Prepare response
            message_data = {
                "sender_id": user.id,
                "content": data["message"],
                "timestamp": new_message.timestamp.isoformat(),
                "is_read": False
            }
            
            # Send to both participants
            await websocket.send_json(message_data)
            await manager.send_personal_message(message_data, user.id, friend_id)
            
    except WebSocketDisconnect:
        manager.disconnect(user.id, friend_id)




# Get chat history
@router.get("/history/{friend_id}", response_model=List[MessageBase])
def get_chat_history(
    friend_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not are_friends(db, current_user.id, friend_id):
        raise HTTPException(status_code=403, detail="Not friends")
    
    return db.query(Message)\
        .filter(
            ((Message.sender_id == current_user.id) &
             (Message.receiver_id == friend_id)) |
            ((Message.sender_id == friend_id) &
             (Message.receiver_id == current_user.id))
        )\
        .order_by(Message.timestamp.asc())\
        .offset((page-1)*page_size)\
        .limit(page_size)\
        .all()  



#get all chats
@router.get("/all")
def get_all_chats(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # PRIVATE CHATS with actual conversation or friends
    message_partners_subq = (
        db.query(
            case(
                (Message.sender_id == current_user.id, Message.receiver_id),
                (Message.receiver_id == current_user.id, Message.sender_id),
                else_=None
            ).label("partner_id")
        )
        .filter(
            or_(
                Message.sender_id == current_user.id,
                Message.receiver_id == current_user.id
            )
        )
        .distinct()
        .subquery()
    )

    partners = db.query(User).join(message_partners_subq, User.id == message_partners_subq.c.partner_id).all()

    private_messages = []
    for user in partners:
        last_msg = (
            db.query(Message)
            .filter(
                or_(
                    and_(Message.sender_id == current_user.id, Message.receiver_id == user.id),
                    and_(Message.receiver_id == current_user.id, Message.sender_id == user.id)
                )
            )
            .order_by(Message.timestamp.desc())
            .first()
        )

        user_info = db.query(UserInfo).filter(UserInfo.user_id == user.id).first()

        private_messages.append({
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}",
            "profile_picture": user_info.profile_picture if user_info else None,
            "last_message": {
                "sender": f"{last_msg.sender.first_name} {last_msg.sender.last_name}" if last_msg else "",
                "content": last_msg.content if last_msg else ""
            }
        })

    # --- GROUP CHATS (unchanged) ---
    groups = (
        db.query(Group)
        .join(group_user_association, group_user_association.c.group_id == Group.id)
        .filter(group_user_association.c.user_id == current_user.id)
        .all()
    )

    group_messages = []
    for group in groups:
        last_msg = (
            db.query(GroupMessage)
            .filter(GroupMessage.group_id == group.id)
            .order_by(GroupMessage.timestamp.desc())
            .first()
        )
        participants = group.members
        group_messages.append({
            "id": group.id,
            "name": group.name,
            "last_message": {
                "sender": f"{last_msg.sender.first_name} {last_msg.sender.last_name}" if last_msg and last_msg.sender else "",
                "content": last_msg.content if last_msg else ""
            },
            "participants_names": [member.first_name for member in participants],
            "participants_ids": [member.id for member in participants]
        })

    return {
        "private_message": private_messages,
        "group_message": group_messages
    }




# Mark message as read
@router.put("/messages/{message_id}/read")
def mark_as_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    message = db.query(Message)\
        .filter(Message.id == message_id)\
        .first()
    
    if not message or message.receiver_id != current_user.id:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.is_read = True
    db.commit()
    return {"status": "marked as read"}  


#Group chat  

class GroupConnectionManager:
    def __init__(self):
        self.active_groups = defaultdict(dict)  # {group_id: {user_id: websocket}}

    async def connect(self, websocket: WebSocket, group_id: int, user_id: int):
        await websocket.accept()
        self.active_groups[group_id][user_id] = websocket

    def disconnect(self, group_id: int, user_id: int):
        if user_id in self.active_groups[group_id]:
            del self.active_groups[group_id][user_id]

    async def broadcast(self, message: dict, group_id: int):
        for connection in self.active_groups[group_id].values():
            await connection.send_json(message)

group_manager = GroupConnectionManager()

@router.websocket("/ws/groups/{group_id}")
async def group_chat_websocket(
    websocket: WebSocket,
    group_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    user = await get_websocket_user(token, db)

    await group_manager.connect(websocket, group_id, user.id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Save message
            new_message = GroupMessage(
                group_id=group_id,
                sender_id=user.id,
                content=data["message"],
                timestamp=datetime.utcnow()
            )
            db.add(new_message)
            db.commit()
            
            # Prepare response
            message_data = {
                "sender_id": user.id,
                "content": data["message"],
                "timestamp": new_message.timestamp.isoformat(),
                "sender_email": user.email
            }
            
            # Broadcast to group
            await group_manager.broadcast(message_data, group_id)
            
    except WebSocketDisconnect:
        group_manager.disconnect(group_id, user.id)          