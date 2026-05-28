import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.permissions import get_current_user
from app.core.rate_limit import (
    LOGIN_LIMIT,
    PASSWORD_RESET_LIMIT,
    REGISTER_LIMIT,
    limiter,
)
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.password_reset_code import PasswordResetCode
from app.models.user import User, UserRole
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.services.email_service import send_password_reset_code

router = APIRouter()


def _build_token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, role=user.role.value),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        role=user.role,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(REGISTER_LIMIT)
def register(
    request: Request,
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    email = payload.email.lower() if payload.email else None
    phone = payload.phone.strip() if payload.phone else None

    if email and db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if phone and db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone number already registered")

    user = User(
        full_name=payload.full_name.strip(),
        email=email,
        phone=phone,
        national_id=payload.national_id,
        password_hash=hash_password(payload.password),
        role=UserRole.citizen,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _build_token_response(user)


def _find_user_by_identifier(db: Session, identifier: str) -> User | None:
    """Resolve a login identifier that may be an email or a phone number."""
    ident = identifier.strip()
    if "@" in ident:
        return db.query(User).filter(User.email == ident.lower()).first()
    # Treat as phone first, then fall back to email (some users type either).
    user = db.query(User).filter(User.phone == ident).first()
    if not user:
        user = db.query(User).filter(User.email == ident.lower()).first()
    return user


def _login(db: Session, identifier: str, password: str, expected_roles: set[UserRole]) -> TokenResponse:
    user = _find_user_by_identifier(db, identifier)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    if user.role not in expected_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong account type for this login")
    return _build_token_response(user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(LOGIN_LIMIT)
def login(
    request: Request,
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    return _login(db, payload.identifier, payload.password, {UserRole.citizen, UserRole.admin})


@router.post("/officer/login", response_model=TokenResponse)
@limiter.limit(LOGIN_LIMIT)
def officer_login(
    request: Request,
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    return _login(db, payload.identifier, payload.password, {UserRole.officer, UserRole.admin})


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    try:
        decoded = decode_token(payload.refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if decoded.get("type") != REFRESH_TOKEN_TYPE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")
    user = db.get(User, int(decoded["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return _build_token_response(user)


@router.post("/logout", response_model=MessageResponse)
def logout(_=Depends(get_current_user)) -> MessageResponse:
    # Stateless JWT — actual invalidation requires a token blacklist (Redis).
    # The frontend should drop the tokens on logout.
    return MessageResponse(message="Logged out")


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit(PASSWORD_RESET_LIMIT)
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    # Don't leak whether the email exists
    if user:
        code = f"{secrets.randbelow(1_000_000):06d}"
        prc = PasswordResetCode(
            user_id=user.id,
            code=code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        db.add(prc)
        db.commit()
        # Best-effort dispatch via SMTP. If EMAIL_ENABLED=false the code is
        # logged at INFO level so devs can still complete the flow.
        send_password_reset_code(to=user.email, full_name=user.full_name, code=code)
    return MessageResponse(message="If the email is registered, a reset code has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest, db: Annotated[Session, Depends(get_db)]
) -> MessageResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")
    prc = (
        db.query(PasswordResetCode)
        .filter(
            PasswordResetCode.user_id == user.id,
            PasswordResetCode.code == payload.code,
            PasswordResetCode.used.is_(False),
        )
        .order_by(PasswordResetCode.id.desc())
        .first()
    )
    if not prc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
    if prc.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired")
    user.password_hash = hash_password(payload.new_password)
    prc.used = True
    db.commit()
    return MessageResponse(message="Password reset successful")


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(
    payload: VerifyEmailRequest, db: Annotated[Session, Depends(get_db)]
) -> MessageResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")
    # Demo: any 6-digit code that matches "000000" or just mark as verified.
    user.is_verified = True
    db.commit()
    return MessageResponse(message="Email verified")
