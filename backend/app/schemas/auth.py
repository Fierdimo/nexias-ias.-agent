from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    company_name: str = Field(..., min_length=2, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class Profile(BaseModel):
    user_id: str
    email: str
    tenant_id: str
    role: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    profile: Profile
    is_demo: bool = False
