from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.database import get_db
from ...schemas.user import Token, UserRead
from ...services import logs_service
from ...services.auth import authenticate_user, create_access_token, get_current_user
from ...services.security_service import SecurityService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/token", response_model=Token)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    security = SecurityService(db)
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        security.record_failed_login(form_data.username, client_ip, user_agent)
        if security.check_bruteforce(form_data.username, client_ip):
            security.maybe_emit_bruteforce_alert(form_data.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logs_service.create_activity_log(
        db,
        user_id=user.id,
        action="login_success",
        metadata={"ip": request.client.host if request.client else None},
    )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        subject=user.email,
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserRead)
def read_users_me(current_user=Depends(get_current_user)):
    return current_user
