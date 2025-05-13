from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from typing import List
from app.db.models.user import User
from app.db.models.group import Group, GroupMessage, group_user_association
from app.db.session import get_db
from app.core.security import get_current_user
from app.schemas.groups import GroupCreate, GroupBase, GroupResponse
from app.schemas.groups import GroupMessage as GroupMessageSchema

router = APIRouter()

# Create group and auto-add creator as member
@router.post("/create", response_model=GroupBase)
def create_group(
    group_data: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_group = Group(
        name=group_data.name,
        owner_id=current_user.id
    )
    # Add creator as a member
    new_group.members.append(current_user)

    # Add other members if provided
    if group_data.member_ids:
        additional_members = db.query(User).filter(User.id.in_(group_data.member_ids)).all()
        for user in additional_members:
            if user not in new_group.members:
                new_group.members.append(user)

    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return new_group


# Add member to group (requires owner/admin)
@router.post("/{group_id}/members")
def add_member(
    group_id: int,
    member_data: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    group = db.query(Group).filter_by(id=group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    users = db.query(User).filter(User.id.in_(member_data)).all()
    for user in users:
        if user not in group.members:
            group.members.append(user)

    db.commit()
    return {"message": f"{len(users)} members added to the group."}


# Get group messages
@router.get("/{group_id}/messages", response_model=List[GroupMessageSchema])
def get_group_messages(
    group_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify current user is in the group
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group or current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a group member")

    return db.query(GroupMessage)\
        .filter(GroupMessage.group_id == group_id)\
        .order_by(GroupMessage.timestamp.asc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()


# Show user's groups
@router.get("/my-groups", response_model=List[GroupResponse])
def get_user_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    groups_query = (
        db.query(
            Group.id,
            Group.name,
            Group.owner_id,
            Group.created_at,
            func.count(group_user_association.c.user_id).label("member_count")
        )
        .join(group_user_association, Group.id == group_user_association.c.group_id)
        .filter(group_user_association.c.user_id == current_user.id)
        .group_by(Group.id)
    )

    paginated_groups = (
        groups_query
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return [
        {
            "id": g.id,
            "name": g.name,
            "owner_id": g.owner_id,
            "created_at": g.created_at,
            "member_count": g.member_count,
            "members": [user.id for user in db.query(User).join(group_user_association).filter(group_user_association.c.group_id == g.id).all()]
        }
        for g in paginated_groups
    ]
