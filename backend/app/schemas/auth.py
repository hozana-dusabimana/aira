from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.user import UserRole


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    # Either an email or a phone number is required (citizens may register
    # with a phone number instead of an email address).
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    national_id: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def _require_email_or_phone(self) -> "RegisterRequest":
        if not self.email and not (self.phone and self.phone.strip()):
            raise ValueError("Provide an email address or a phone number")
        return self


class LoginRequest(BaseModel):
    # Accept either an explicit `identifier` (email OR phone) or the legacy
    # `email` field for backward compatibility.
    identifier: str | None = None
    email: str | None = None
    password: str

    @model_validator(mode="after")
    def _coalesce_identifier(self) -> "LoginRequest":
        ident = (self.identifier or self.email or "").strip()
        if not ident:
            raise ValueError("Provide an email or phone number")
        self.identifier = ident
        return self


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    role: UserRole


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=10)
    new_password: str = Field(min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=10)


class MessageResponse(BaseModel):
    message: str
