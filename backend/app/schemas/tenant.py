from pydantic import BaseModel, Field


class TenantInfo(BaseModel):
    tenant_id: str
    name: str
    sheet_id: str | None = None
    sheet_configured: bool = False
    # Email del service account: con quién compartir la Google Sheet.
    service_account_email: str | None = None
    is_demo: bool = False


class SetSheetRequest(BaseModel):
    # Acepta el ID pelado o la URL completa de Google Sheets.
    sheet: str = Field(..., min_length=8, max_length=400)
