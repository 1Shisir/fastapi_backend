from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.db.models.user import User
from app.db.models.group import Group, GroupMember, GroupMessage
from app.db.session import get_db
from app.core.security import get_current_user, is_group_member, is_group_admin
from app.schemas.groups import GroupCreate, GroupMemberAdd,GroupBase, GroupResponse
from app.schemas.groups import GroupMessage as GroupMessageSchema

router = APIRouter()

# Create group
@router.post("/", response_model=GroupBase)
def create_group(
    group_data: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_group = Group(
        name=group_data.name,
        description=group_data.description,
        owner_id=current_user.id
    )
    
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    
    # Add owner as admin
    db.add(GroupMember(
        group_id=new_group.id,
        user_id=current_user.id,
        role='admin'
    ))
    db.commit()
    
    return new_group

# Add member to group
@router.post("/{group_id}/members")
def add_member(
    group_id: int,
    member_data: GroupMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    group = db.query(Group).get(group_id)
    if not group or not is_group_admin(db, group_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    new_member = GroupMember(
        group_id=group_id,
        user_id=member_data.user_id,
        role=member_data.role
    )
    
    db.add(new_member)
    db.commit()
    return {"message": "Member added"}

# Get group messages
@router.get("/{group_id}/messages", response_model=List[GroupMessageSchema])
def get_group_messages(
    group_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not is_group_member(db, group_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a group member")
    
    return db.query(GroupMessage)\
        .filter(GroupMessage.group_id == group_id)\
        .order_by(GroupMessage.timestamp.desc())\
        .offset((page-1)*page_size)\
        .limit(page_size)\
        .all()



#show users groups
@router.get("/my-groups", response_model=List[GroupResponse])
def get_user_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get groups where user is a member
    groups_query = db.query(
        Group.id,
        Group.name,
        Group.description,
        Group.owner_id,
        Group.created_at,
        GroupMember.role.label('your_role'),
        GroupMember.joined_at,
        func.count(GroupMember.user_id).label('member_count')
    ).join(GroupMember, Group.id == GroupMember.group_id)\
     .filter(GroupMember.user_id == current_user.id)\
     .group_by(Group.id, GroupMember.role, GroupMember.joined_at)

    # Apply pagination
    paginated_groups = groups_query.offset((page-1)*page_size)\
                                   .limit(page_size)\
                                   .all()

    # Format response
    return [{
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "owner_id": group.owner_id,
        "created_at": group.created_at,
        "member_count": group.member_count,
        "your_role": group.your_role,
        "joined_at": group.joined_at
    } for group in paginated_groups]