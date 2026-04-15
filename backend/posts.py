import os
import uuid
from datetime import datetime, timezone

from auth import require_admin
from database import get_db
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from models import Brand, Post
from pydantic import BaseModel
from sqlalchemy import extract, func

router = APIRouter(prefix="/api/admin", tags=["posts"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_MEDIA_BUCKET", "post-media")

_LOCAL_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class BrandCreate(BaseModel):
    name: str
    monthly_story_goal: int | None = None
    monthly_reel_goal: int | None = None


class BrandUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    monthly_story_goal: int | None = None
    monthly_reel_goal: int | None = None


class BrandOut(BaseModel):
    id: int
    name: str
    is_active: bool
    monthly_story_goal: int | None
    monthly_reel_goal: int | None
    created_at: datetime

    class Config:
        from_attributes = True


class PostCreate(BaseModel):
    brand_id: int
    type: str  # "story" | "reel"
    posted_at: datetime
    notes: str | None = None
    media_url: str | None = None


class PostUpdate(BaseModel):
    brand_id: int | None = None
    type: str | None = None
    posted_at: datetime | None = None
    notes: str | None = None
    media_url: str | None = None


class PostOut(BaseModel):
    id: int
    brand_id: int
    brand_name: str
    type: str
    posted_at: datetime
    notes: str | None
    media_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _upload_to_supabase(file_bytes: bytes, filename: str, content_type: str) -> str:
    from supabase import create_client

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    path = f"posts/{filename}"
    client.storage.from_(SUPABASE_BUCKET).upload(
        path,
        file_bytes,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    public_url = client.storage.from_(SUPABASE_BUCKET).get_public_url(path)
    return public_url


def _upload_local(file_bytes: bytes, filename: str) -> str:
    os.makedirs(_LOCAL_UPLOAD_DIR, exist_ok=True)
    dest = os.path.join(_LOCAL_UPLOAD_DIR, filename)
    with open(dest, "wb") as f:
        f.write(file_bytes)
    return f"/static/uploads/{filename}"


def _is_supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    _=Depends(require_admin),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    ext = os.path.splitext(file.filename or "")[-1].lower() or ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_bytes = await file.read()

    if _is_supabase_configured():
        url = _upload_to_supabase(file_bytes, unique_name, file.content_type)
    else:
        url = _upload_local(file_bytes, unique_name)

    return {"url": url, "filename": unique_name}


# ---------------------------------------------------------------------------
# Brand routes
# ---------------------------------------------------------------------------


@router.get("/brands", response_model=list[BrandOut])
def list_brands(_=Depends(require_admin)):
    with get_db() as db:
        return db.query(Brand).order_by(Brand.name).all()


@router.post("/brands", response_model=BrandOut, status_code=status.HTTP_201_CREATED)
def create_brand(data: BrandCreate, _=Depends(require_admin)):
    with get_db() as db:
        existing = db.query(Brand).filter(Brand.name == data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Brand name already exists")
        brand = Brand(**data.model_dump())
        db.add(brand)
        db.commit()
        db.refresh(brand)
        return brand


@router.put("/brands/{brand_id}", response_model=BrandOut)
def update_brand(brand_id: int, data: BrandUpdate, _=Depends(require_admin)):
    with get_db() as db:
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(brand, field, value)
        db.commit()
        db.refresh(brand)
        return brand


@router.delete("/brands/{brand_id}")
def delete_brand(brand_id: int, _=Depends(require_admin)):
    with get_db() as db:
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        has_posts = db.query(Post).filter(Post.brand_id == brand_id).first()
        if has_posts:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete brand with existing posts. Deactivate it instead.",
            )
        db.delete(brand)
        db.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Post routes
# ---------------------------------------------------------------------------


@router.get("/posts", response_model=list[PostOut])
def list_posts(
    brand_id: int | None = Query(default=None),
    _=Depends(require_admin),
):
    with get_db() as db:
        q = db.query(Post, Brand.name.label("brand_name")).join(Brand, Post.brand_id == Brand.id)
        if brand_id:
            q = q.filter(Post.brand_id == brand_id)
        rows = q.order_by(Post.posted_at.desc()).all()
        result = []
        for post, brand_name in rows:
            result.append(
                PostOut(
                    id=post.id,
                    brand_id=post.brand_id,
                    brand_name=brand_name,
                    type=post.type,
                    posted_at=post.posted_at,
                    notes=post.notes,
                    media_url=post.media_url,
                    created_at=post.created_at,
                )
            )
        return result


@router.post("/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(data: PostCreate, _=Depends(require_admin)):
    with get_db() as db:
        brand = db.query(Brand).filter(Brand.id == data.brand_id).first()
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        if data.type not in ("story", "reel"):
            raise HTTPException(status_code=400, detail="type must be 'story' or 'reel'")
        post = Post(**data.model_dump())
        db.add(post)
        db.commit()
        db.refresh(post)
        return PostOut(
            id=post.id,
            brand_id=post.brand_id,
            brand_name=brand.name,
            type=post.type,
            posted_at=post.posted_at,
            notes=post.notes,
            media_url=post.media_url,
            created_at=post.created_at,
        )


@router.put("/posts/{post_id}", response_model=PostOut)
def update_post(post_id: int, data: PostUpdate, _=Depends(require_admin)):
    with get_db() as db:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        if data.type and data.type not in ("story", "reel"):
            raise HTTPException(status_code=400, detail="type must be 'story' or 'reel'")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(post, field, value)
        db.commit()
        db.refresh(post)
        brand = db.query(Brand).filter(Brand.id == post.brand_id).first()
        return PostOut(
            id=post.id,
            brand_id=post.brand_id,
            brand_name=brand.name,
            type=post.type,
            posted_at=post.posted_at,
            notes=post.notes,
            media_url=post.media_url,
            created_at=post.created_at,
        )


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, _=Depends(require_admin)):
    with get_db() as db:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        db.delete(post)
        db.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/posts/stats")
def posts_stats(_=Depends(require_admin)):
    """Returns per-brand stats for the current month vs monthly goals."""
    now = datetime.now(tz=timezone.utc)
    current_month = now.month
    current_year = now.year

    with get_db() as db:
        brands = db.query(Brand).order_by(Brand.name).all()
        result = []
        for brand in brands:
            stories_done = (
                db.query(func.count(Post.id))
                .filter(
                    Post.brand_id == brand.id,
                    Post.type == "story",
                    extract("month", Post.posted_at) == current_month,
                    extract("year", Post.posted_at) == current_year,
                )
                .scalar()
                or 0
            )
            reels_done = (
                db.query(func.count(Post.id))
                .filter(
                    Post.brand_id == brand.id,
                    Post.type == "reel",
                    extract("month", Post.posted_at) == current_month,
                    extract("year", Post.posted_at) == current_year,
                )
                .scalar()
                or 0
            )
            total_posts = (
                db.query(func.count(Post.id)).filter(Post.brand_id == brand.id).scalar() or 0
            )
            result.append(
                {
                    "brand_id": brand.id,
                    "brand_name": brand.name,
                    "is_active": brand.is_active,
                    "monthly_story_goal": brand.monthly_story_goal,
                    "monthly_reel_goal": brand.monthly_reel_goal,
                    "stories_this_month": stories_done,
                    "reels_this_month": reels_done,
                    "total_posts": total_posts,
                }
            )
        return result
