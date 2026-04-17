import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from auth import require_admin
from database import get_db
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from models import Click, Link
from pydantic import BaseModel
from sqlalchemy import func

UPLOADS_DIR = Path(__file__).parent / "uploads"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_MEDIA_BUCKET", "post-media")


def _is_supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _upload_coupon_to_supabase(file_bytes: bytes, filename: str, content_type: str) -> str:
    from supabase import create_client

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    path = f"coupons/{filename}"
    client.storage.from_(SUPABASE_BUCKET).upload(
        path,
        file_bytes,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return client.storage.from_(SUPABASE_BUCKET).get_public_url(path)


def _upload_coupon_local(file_bytes: bytes, filename: str) -> str:
    UPLOADS_DIR.mkdir(exist_ok=True)
    (UPLOADS_DIR / filename).write_bytes(file_bytes)
    return f"/uploads/{filename}"

router = APIRouter(prefix="/api/admin", tags=["admin"])


# --- Schemas ---


class LinkCreate(BaseModel):
    slug: str
    title: str
    description: str | None = None
    destination_url: str
    coupon_code: str | None = None
    coupon_image_url: str | None = None
    icon: str | None = None
    category: str = "produto"


class LinkUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    destination_url: str | None = None
    coupon_code: str | None = None
    coupon_image_url: str | None = None
    icon: str | None = None
    category: str | None = None
    is_active: bool | None = None


class LinkAdminOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None
    destination_url: str
    coupon_code: str | None
    coupon_image_url: str | None
    icon: str | None
    category: str
    is_active: bool
    created_at: datetime
    clicks: int

    class Config:
        from_attributes = True


# --- Routes ---


@router.post("/upload-coupon-image", status_code=status.HTTP_200_OK)
async def upload_coupon_image(
    file: UploadFile = File(...),
    _=Depends(require_admin),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não permitido")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Arquivo muito grande (máx 10 MB)")

    fname = file.filename or ""
    ext = fname.rsplit(".", 1)[-1] if "." in fname else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"

    if _is_supabase_configured():
        url = _upload_coupon_to_supabase(contents, filename, file.content_type)
    else:
        url = _upload_coupon_local(contents, filename)

    return {"url": url}


@router.get("/links", response_model=list[LinkAdminOut])
def admin_list_links(_=Depends(require_admin)):
    with get_db() as db:
        rows = (
            db.query(Link, func.count(Click.id).label("clicks"))
            .outerjoin(Click, Click.link_id == Link.id)
            .group_by(Link.id)
            .order_by(Link.created_at.desc())
            .all()
        )
        result = []
        for link, clicks in rows:
            out = LinkAdminOut(
                id=link.id,
                slug=link.slug,
                title=link.title,
                description=link.description,
                destination_url=link.destination_url,
                coupon_code=link.coupon_code,
                coupon_image_url=link.coupon_image_url,
                icon=link.icon,
                category=link.category,
                is_active=link.is_active,
                created_at=link.created_at,
                clicks=clicks,
            )
            result.append(out)
        return result


@router.post("/links", response_model=LinkAdminOut, status_code=status.HTTP_201_CREATED)
def admin_create_link(data: LinkCreate, _=Depends(require_admin)):
    with get_db() as db:
        exists = db.query(Link).filter(Link.slug == data.slug).first()
        if exists:
            raise HTTPException(status_code=400, detail="Slug already exists")

        link = Link(**data.model_dump())
        db.add(link)
        db.commit()
        db.refresh(link)

        return LinkAdminOut(
            id=link.id,
            slug=link.slug,
            title=link.title,
            description=link.description,
            destination_url=link.destination_url,
            coupon_code=link.coupon_code,
            coupon_image_url=link.coupon_image_url,
            icon=link.icon,
            category=link.category,
            is_active=link.is_active,
            created_at=link.created_at,
            clicks=0,
        )


@router.put("/links/{link_id}", response_model=LinkAdminOut)
def admin_update_link(link_id: int, data: LinkUpdate, _=Depends(require_admin)):
    with get_db() as db:
        link = db.query(Link).filter(Link.id == link_id).first()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(link, field, value)

        db.commit()
        db.refresh(link)

        clicks = db.query(func.count(Click.id)).filter(Click.link_id == link.id).scalar() or 0

        return LinkAdminOut(
            id=link.id,
            slug=link.slug,
            title=link.title,
            description=link.description,
            destination_url=link.destination_url,
            coupon_code=link.coupon_code,
            coupon_image_url=link.coupon_image_url,
            icon=link.icon,
            category=link.category,
            is_active=link.is_active,
            created_at=link.created_at,
            clicks=clicks,
        )


@router.delete("/links/{link_id}")
def admin_deactivate_link(link_id: int, _=Depends(require_admin)):
    with get_db() as db:
        link = db.query(Link).filter(Link.id == link_id).first()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")

        link.is_active = False
        db.commit()

        return {"ok": True}


@router.delete("/links/{link_id}/hard")
def admin_hard_delete_link(link_id: int, _=Depends(require_admin)):
    with get_db() as db:
        link = db.query(Link).filter(Link.id == link_id).first()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")

        db.query(Click).filter(Click.link_id == link_id).delete()
        db.delete(link)
        db.commit()

        return {"ok": True}


# --- Analytics Routes ---


@router.get("/analytics/clicks-per-link")
def analytics_clicks_per_link(
    days: int = Query(default=30, ge=1, le=365),
    _=Depends(require_admin),
):
    since = datetime.utcnow() - timedelta(days=days)
    with get_db() as db:
        rows = (
            db.query(Link.slug, Link.title, func.count(Click.id).label("clicks"))
            .outerjoin(
                Click,
                (Click.link_id == Link.id) & (Click.timestamp >= since),
            )
            .group_by(Link.id)
            .order_by(func.count(Click.id).desc())
            .all()
        )
        return [{"slug": r.slug, "title": r.title, "clicks": r.clicks} for r in rows]


@router.get("/analytics/clicks-per-day")
def analytics_clicks_per_day(
    days: int = Query(default=30, ge=1, le=365),
    _=Depends(require_admin),
):
    since = datetime.utcnow() - timedelta(days=days)
    with get_db() as db:
        rows = (
            db.query(
                func.date(Click.timestamp).label("date"),
                func.count(Click.id).label("clicks"),
            )
            .filter(Click.timestamp >= since)
            .group_by(func.date(Click.timestamp))
            .order_by(func.date(Click.timestamp).desc())
            .all()
        )
        return [{"date": str(r.date), "clicks": r.clicks} for r in rows]


@router.get("/analytics/clicks-per-source")
def analytics_clicks_per_source(
    days: int = Query(default=30, ge=1, le=365),
    _=Depends(require_admin),
):
    since = datetime.utcnow() - timedelta(days=days)
    with get_db() as db:
        rows = (
            db.query(
                func.coalesce(Click.source, "(direto)").label("source"),
                func.count(Click.id).label("clicks"),
            )
            .filter(Click.timestamp >= since)
            .group_by(func.coalesce(Click.source, "(direto)"))
            .order_by(func.count(Click.id).desc())
            .all()
        )
        return [{"source": r.source, "clicks": r.clicks} for r in rows]
