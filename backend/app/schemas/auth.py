from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional

from app.models import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    role: Optional[UserRole] = UserRole.ENTREPRENEUR


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    two_factor_code: Optional[str] = None


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_two_factor_enabled: bool
    is_email_verified: bool

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str
    requires_2fa: bool = False


class TokenData(BaseModel):
    email: str | None = None


class TwoFactorSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class TwoFactorVerifyRequest(BaseModel):
    code: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetResponse(BaseModel):
    message: str