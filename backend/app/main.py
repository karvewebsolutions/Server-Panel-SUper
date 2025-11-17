from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .api.routes import auth, health
from .core.config import get_settings
from .core.database import Base, engine, get_db
from .models.user import User
from .services.auth import get_password_hash

settings = get_settings()


def init_database():
    Base.metadata.create_all(bind=engine)


def seed_admin(db: Session):
    admin = db.query(User).filter(User.email == settings.admin_email).first()
    if not admin:
        admin = User(
            email=settings.admin_email,
            hashed_password=get_password_hash(settings.admin_password),
            role="admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)


@asynccontextmanager
def lifespan(app: FastAPI):
    init_database()
    with next(get_db()) as db:
        seed_admin(db)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    return app


app = create_app()


@app.get("/")
def root():
    return {"message": "KWS Control Panel API"}
