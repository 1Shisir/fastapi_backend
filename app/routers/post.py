from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional
import time
import logging
from cloudinary import uploader
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from app.db.models.user import User
from app.db.models.like import Like
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.post import  PostOut, PostOutWithUserLike
from app.core.security import get_current_user
from app.db.models.post import Post
from cloudinary.exceptions import Error as CloudinaryError

router = APIRouter()

@router.get("/", response_model=list[PostOutWithUserLike])
def get_all_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get all posts with user relationship loaded
    posts = db.query(Post)\
        .options(joinedload(Post.user))\
        .all()
    
    if not posts:
        raise HTTPException(status_code=404, detail="No posts found")

    # Get IDs of posts liked by current user
    post_ids = [post.id for post in posts]
    liked_posts = db.query(Like.post_id).filter(
        Like.user_id == current_user.id,
        Like.post_id.in_(post_ids)
    ).all()
    liked_post_ids = {post_id for (post_id,) in liked_posts}

    # Build response with author name and like status
    return [
        {
            "id": post.id,
            "user_id": post.user_id,
            "likes_count": post.likes_count,
            "content": post.content,
            "image_url": post.image_url,
            "created_at": post.created_at,
            "author_name": f"{post.user.first_name} {post.user.last_name}",
            "is_liked_by_me": post.id in liked_post_ids
        }
        for post in posts
    ]



# Create a new post
@router.post("/create", response_model=PostOut)
async def create_post(
    content: str = Form(...),
    post_image: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # try:
    #     # Parse and validate post content
    #     post_data = json.loads(content)
    #     post_content = PostCreate(**post_data)
    # except (json.JSONDecodeError, ValidationError) as e:
    #     raise HTTPException(
    #         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    #         detail=str(e)
    #     )

    image_data = {}
    
    if post_image and post_image.filename and post_image.size > 0:

        try:
            # Validate image
            if post_image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
                raise HTTPException(400, "Invalid image format")
            if post_image.size > 5 * 1024 * 1024:  # 5MB
                raise HTTPException(400, "File too large (max 5MB)")

            # Upload to Cloudinary
            upload_result = uploader.upload(
                await post_image.read(),
                folder="post_images",
                public_id=f"post_{current_user.id}_{int(time.time())}",
                resource_type="image",
                overwrite=True,
                quality="auto:good"
            )
            
            image_data = {
                "image_url": upload_result["secure_url"],
                "image_public_id": upload_result["public_id"]
            }
        except CloudinaryError as e:
            logging.error(f"Cloudinary Error: {str(e)}")
            raise HTTPException(500, f"Image upload failed: {e}")

    try:
        new_post = Post(
            user_id=current_user.id,
            content=content,
            **image_data
        )
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        return new_post
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error: {str(e)}")
        # Cleanup uploaded image if database operation failed
        if image_data.get("image_public_id"):
            try:
                uploader.destroy(image_data["image_public_id"])
            except CloudinaryError as ce:
                logging.error(f"Cloudinary cleanup error: {str(ce)}")
        raise HTTPException(500, "Failed to create post")

#get post of current user
@router.get("/me", response_model=list[PostOut])
def get_my_posts(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    post = db.query(Post).filter(Post.user_id == current_user.id).all()
    if not post:
        raise HTTPException(status_code=404, detail="No posts found")
    return post


@router.get("/{post_id}", response_model=PostOut)
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
@router.delete("/{post_id}")
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
    return {"msg": message}  