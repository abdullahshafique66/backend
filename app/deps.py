from datetime import date, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)
DB = Annotated[Session, Depends(get_db)]


def current_user(db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login zaroori hai.", headers={"WWW-Authenticate": "Bearer"})
    uid = decode_token(creds.credentials)
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session khatam ho gaya, dobara login karein.", headers={"WWW-Authenticate": "Bearer"})
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def today() -> date:
    """'Today' in the configured household timezone (Asia/Karachi by default)."""
    return datetime.now(get_settings().tz).date()
