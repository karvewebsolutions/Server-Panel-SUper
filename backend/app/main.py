from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .api import api_router
from .core.config import get_settings
from .core.database import Base, engine, get_db
from .models.user import User
from .services.auth import get_password_hash

settings = get_settings()


def init_database():
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
def lifespan(app: FastAPI):
    init_database()
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
    app.include_router(api_router)
    return app


app = create_app()


@app.get("/")
def root():
    return {"message": "KWS Control Panel API"}
