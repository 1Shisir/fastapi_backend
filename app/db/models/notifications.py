from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String)
    is_read = Column(Boolean, default=False)
    type = Column(String)  # 'connection_request', 'request_accepted', etc.
    related_request_id = Column(Integer, ForeignKey("connection_requests.id"))
    related_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications", foreign_keys=[user_id])
    related_user = relationship("User", foreign_keys=[related_user_id])
