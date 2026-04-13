from datetime import datetime
from pathlib import Path

from database import Base, engine, get_db
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from models import Click, Link
from pydantic import BaseModel
from sqlalchemy import func

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="Clara Braga — Links")

INITIAL_LINKS = [
    {
        "slug": "whey",
        "title": "Whey Protein",
        "description": "O whey que eu uso todo dia. Resultado garantido!",
        "destination_url": "https://www.integral-medica.com.br",
        "coupon_code": "CLARA10",
        "category": "produto",
    },
    {
        "slug": "creatina",
        "title": "Creatina",
        "description": "A creatina que faz parte da minha rotina há anos.",
        "destination_url": "https://www.integral-medica.com.br",
        "coupon_code": "CLARACREA",
        "category": "produto",
    },
    {
        "slug": "colageno",
        "title": "Colágeno",
        "description": "Pele, cabelo e articulação — tudo em um só produto.",
        "destination_url": "https://www.integral-medica.com.br",
        "coupon_code": "CLARACOL",
        "category": "produto",
    },
    {
        "slug": "desconto",
        "title": "Cupom Especial 15% OFF",
        "description": "Use meu cupom e garanta 15% de desconto em qualquer produto.",
        "destination_url": "https://www.integral-medica.com.br",
        "coupon_code": "CLARA15",
        "category": "cupom",
    },
    {
        "slug": "pre-treino",
        "title": "Pré-Treino",
        "description": "Energia e foco para arrasar nos treinos.",
        "destination_url": "https://www.integral-medica.com.br",
        "coupon_code": "CLARAPRE",
        "category": "produto",
    },
]


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    with get_db() as db:
        for data in INITIAL_LINKS:
            exists = db.query(Link).filter(Link.slug == data["slug"]).first()
            if not exists:
                db.add(Link(**data))
        db.commit()


# --- Static files (CSS, assets) ---
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# --- Frontend ---
@app.get("/", include_in_schema=False)
def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


# --- API ---
class LinkOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None
    coupon_code: str | None
    category: str

    class Config:
        from_attributes = True


@app.get("/api/links", response_model=list[LinkOut])
def list_links():
    with get_db() as db:
        return db.query(Link).filter(Link.is_active == True).all()  # noqa: E712


@app.get("/api/stats")
def stats():
    with get_db() as db:
        rows = (
            db.query(Link.slug, Link.title, func.count(Click.id).label("clicks"))
            .outerjoin(Click, Click.link_id == Link.id)
            .group_by(Link.id)
            .all()
        )
        return [{"slug": r.slug, "title": r.title, "clicks": r.clicks} for r in rows]


# --- Redirect + tracking ---
@app.get("/{slug}", include_in_schema=False)
def redirect_link(slug: str, request: Request, src: str | None = None):
    with get_db() as db:
        link = db.query(Link).filter(Link.slug == slug, Link.is_active == True).first()  # noqa: E712
        if not link:
            raise HTTPException(status_code=404, detail="Link não encontrado")

        click = Click(
            link_id=link.id,
            timestamp=datetime.utcnow(),
            source=src,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(click)
        db.commit()

        return RedirectResponse(url=link.destination_url, status_code=302)
