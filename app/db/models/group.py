from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.db.base import Base

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User")
    members = relationship("GroupMember", back_populates="group")
    messages = relationship("GroupMessage", back_populates="group")

class GroupMember(Base):
    __tablename__ = "group_members"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(Enum('member', 'admin', name="group_roles"), default='member')
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    group = relationship("Group", back_populates="members")
    user = relationship("User")

class GroupMessage(Base):
    __tablename__ = "group_messages"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    group = relationship("Group", back_populates="messages")
    sender = relationship("User")