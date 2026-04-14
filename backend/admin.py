from datetime import datetime, timedelta

from auth import require_admin
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models import Click, Link
from pydantic import BaseModel
from sqlalchemy import func

router = APIRouter(prefix="/api/admin", tags=["admin"])


# --- Schemas ---


class LinkCreate(BaseModel):
    slug: str
    title: str
    description: str | None = None
    destination_url: str
    coupon_code: str | None = None
    icon: str | None = None
    category: str = "produto"


class LinkUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    destination_url: str | None = None
    coupon_code: str | None = None
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
    icon: str | None
    category: str
    is_active: bool
    created_at: datetime
    clicks: int

    class Config:
        from_attributes = True


# --- Routes ---


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
