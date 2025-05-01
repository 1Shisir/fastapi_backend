from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas import post as schemas
from app.crud import post as crud
from app.core.security import get_current_user
from app.db.models.post import Post

router = APIRouter()

@router.post("/", response_model=schemas.PostOut)
def create_post(
    post: schemas.PostCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return crud.create_post(db, post, user_id=current_user.id)

#get post of current user
@router.get("/me", response_model=list[schemas.PostOut])
def get_my_posts(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    post = db.query(Post).filter(Post.user_id == current_user.id).all()
    if not post:
        raise HTTPException(status_code=404, detail="No posts found")
    return post


@router.get("/", response_model=list[schemas.PostOut])
def get_posts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_posts(db, skip=skip, limit=limit)


@router.get("/{post_id}", response_model=schemas.PostOut)
def get_post_by_id(
    post_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post  

#delete post
@router.delete("/{post_id}", response_model=schemas.PostOut)
def delete_post(
    post_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    message = "Post deleted successfully"    
    db.delete(post)
    db.commit()
    return {"msg": message, "post": PostOut.from_orm(post)}      