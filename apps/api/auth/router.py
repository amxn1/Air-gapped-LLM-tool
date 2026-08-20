from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Any

from .. import models
from .config import (
    create_access_token,
    create_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    ALGORITHM
)
from . import crud, schemas as auth_schemas
from ..database import get_db

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post("/token", response_model=auth_schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Any:
    """
    OAuth2 compatible token login, get an access token and refresh token for future requests.
    """
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh_token", response_model=auth_schemas.Token)
async def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    Refresh an access token using a refresh token.
    """
    from jose import JWTError, jwt

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = crud.get_user_by_username(db, username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.get("/users/me", response_model=auth_schemas.User)
async def read_users_me(
    current_user: models.User = Depends(crud.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user


@router.get("/users/{username}", response_model=auth_schemas.User)
async def read_user(
    username: str,
    current_user: models.User = Depends(crud.get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Get a specific user by username.
    """
    user = crud.get_user_by_username(db, username=username)
    if user and (user.id == current_user.id or crud.is_admin(current_user)):
        return user
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    raise HTTPException(
        status_code=403, detail="The user doesn't have enough privileges"
    )