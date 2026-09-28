import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select

from .. import schemas
from ..deps import DB, CurrentUser
from ..models import PasswordReset, User
from ..security import create_token, hash_password, verify_password
from ..services.seed import create_default_categories

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger("apna_hisab.auth")


def _session(user: User) -> schemas.SessionOut:
    return schemas.SessionOut(token=create_token(user.id), user=schemas.UserOut.model_validate(user))


@router.post("/signup", response_model=schemas.SessionOut, status_code=status.HTTP_201_CREATED)
def signup(body: schemas.SignupIn, db: DB):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Is email se account pehle se bana hua hai. Login karein.")
    user = User(name=body.name.strip(), email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    create_default_categories(db, user)
    db.commit()
    return _session(user)


@router.post("/login", response_model=schemas.SessionOut)
def login(body: schemas.LoginIn, db: DB):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ya password ghalat hai.")
    return _session(user)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(body: schemas.ForgotIn, db: DB):
    """Always 204 (never reveals whether the email exists).
    The reset link is logged to the server console until an email service (SMTP) is configured."""
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user:
        token = secrets.token_urlsafe(32)
        db.add(PasswordReset(token=token, user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(minutes=30)))
        db.commit()
        log.warning("Password reset link for %s: /reset-password?token=%s", user.email, token)


@router.post("/reset-password", response_model=schemas.SessionOut)
def reset_password(body: schemas.ResetIn, db: DB):
    pr = db.get(PasswordReset, body.token)
    exp = pr.expires_at.replace(tzinfo=timezone.utc) if pr and pr.expires_at.tzinfo is None else (pr.expires_at if pr else None)
    if not pr or exp < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reset link expire ho gaya hai. Dobara request karein.")
    user = db.get(User, pr.user_id)
    user.password_hash = hash_password(body.password)
    db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id))
    db.commit()
    return _session(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: schemas.ChangePasswordIn, user: CurrentUser, db: DB):
    if not verify_password(body.current, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password ghalat hai.")
    user.password_hash = hash_password(body.next)
    db.commit()
