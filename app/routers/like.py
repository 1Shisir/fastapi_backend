from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas import post as schemas
from app.schemas.post import PostOut
from app.db.models.post import Post
from app.db.models.like import Like
from app.core.security import get_current_user

router = APIRouter(prefix="/like", tags=["Likes"])

@router.post("/{post_id}")
def toogle_like(
    post_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    #Check if the user has already liked the post

    existing_like = db.query(Like).filter(
        Like.user_id == current_user.id,
        Like.post_id == post_id
    ).first()

    if existing_like:
        # If the user has already liked the post, remove the like
        db.delete(existing_like)
        post.likes_count -= 1
        message = "Like removed"
    else:
        # If the user has not liked the post, add a like
        new_like = Like(user_id=current_user.id, post_id=post_id)
        db.add(new_like)
        post.likes_count += 1
        message = "Post liked"
    db.commit()

    return {
        "message": message,
        "post": PostOut.from_orm(post),
    }