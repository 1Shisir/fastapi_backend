from fastapi import FastAPI
from app.api.v1 import auth, user
from app.db.base import Base
from app.db.session import engine
from app.routers import post
from app.routers import like
from app.routers import admin
from app.routers import connections
from app.routers import chat
from app.routers import groups

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(user.router, prefix="/api/users", tags=["Users"])
app.include_router(post.router, prefix="/api/posts", tags=["Posts"])
app.include_router(like.router, prefix="/api/likes", tags=["Likes"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(connections.router, prefix="/api/connections", tags=["Connections"])
app.include_router(chat.router, prefix="/api/chat", tags=["Messages"])
app.include_router(groups.router, prefix="/api/groups", tags=["Groups"])