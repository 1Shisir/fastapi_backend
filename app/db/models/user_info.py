from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Boolean
from datetime import datetime
from sqlalchemy.orm import relationship
from app.db.base import Base

class UserInfo(Base):
    __tablename__ = "user_info"

    id = Column(Integer, primary_key=True, index=True , autoincrement=True)
    address = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    dob = Column(Date, nullable=True)
    passions = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    lifestyle = Column(String, nullable=True)
    dietary = Column(String, nullable=True)
    available = Column(Boolean, default=False)
    religion = Column(String, nullable=True)
    number_of_children = Column(Integer, nullable=True)
    profile_picture = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    profile_public_id = Column(String, nullable=True)

    user = relationship("User", back_populates="user_info")

