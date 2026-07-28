from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api import admin, public
from app.config import get_settings
from app.db import SessionLocal, init_db
from app.services.seed import load_persons_csv, load_seed_csv

ROOT = Path(__file__).resolve().parents[3]


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.2.0")
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(public.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")

    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.on_event("startup")
    def _startup() -> None:
        init_db()
        Path(settings.storage_dir).joinpath("exports").mkdir(parents=True, exist_ok=True)
        seed_path = Path(settings.seed_csv_path)
        if not seed_path.is_file():
            alt = ROOT / "data" / "seed" / "institutions.csv"
            if alt.is_file():
                seed_path = alt
        if seed_path.is_file():
            db = SessionLocal()
            try:
                load_seed_csv(db, seed_path)
                load_persons_csv(db, seed_path.with_name("persons.csv"))
            finally:
                db.close()

    @app.get("/", response_class=HTMLResponse)
    def admin_ui() -> str:
        return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")

    return app


app = create_app()
