from pydantic import BaseModel, Field


class ConnectRequest(BaseModel):
    server_auth_code: str = Field(..., min_length=10, max_length=2000)
    # El flujo nativo de Google Sign-In (serverAuthCode) no usa redirect_uri.
    redirect_uri: str | None = None
    code_verifier: str | None = None


class PickedFile(BaseModel):
    id: str
    name: str | None = None
    mimeType: str | None = None


class SourcesRequest(BaseModel):
    files: list[PickedFile] = Field(default_factory=list, max_length=50)


class GoogleStatus(BaseModel):
    oauth_configured: bool
    connected: bool
    email: str | None = None
    sources: list[PickedFile] = Field(default_factory=list)
    is_demo: bool = False
