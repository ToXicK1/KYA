from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str = Field(..., description="JWT Bearer Token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Expiration duration in seconds")


class TokenData(BaseModel):
    username: str
    organization: str
    roles: list[str] = []


class LoginRequest(BaseModel):
    username: str = Field(
        ...,
        json_schema_extra={"example": "admin_google"},
        description="Administrator username",
    )
    password: str = Field(
        ...,
        json_schema_extra={"example": "••••••••"},
        description="Administrator password",
    )
    organization: str = Field(
        ...,
        json_schema_extra={"example": "org_google_cloud"},
        description="Organization identifier",
    )
