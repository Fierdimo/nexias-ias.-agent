"""Configuración de la empresa: ver y asignar su Google Sheet.

Solo el rol `admin` puede cambiar la hoja. En modo demo devuelve datos
ficticios y la escritura es no-op.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.schemas.tenant import SetSheetRequest, TenantInfo
from app.services.sheets import extract_sheet_id, service_account_email
from app.services.tenants import get_tenant, set_tenant_sheet

router = APIRouter(prefix="/tenant", tags=["tenant"])


def _info(
    tenant_id: str, name: str, sheet_id: str | None, is_demo: bool
) -> TenantInfo:
    return TenantInfo(
        tenant_id=tenant_id,
        name=name,
        sheet_id=sheet_id,
        sheet_configured=bool(sheet_id),
        service_account_email=service_account_email(),
        is_demo=is_demo,
    )


@router.get("", response_model=TenantInfo)
def read_tenant(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> TenantInfo:
    if not settings.has_supabase:
        return _info(user.tenant_id, "Empresa demo", None, True)
    tenant = get_tenant(user.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return _info(
        user.tenant_id, tenant["name"], tenant.get("sheet_id"), False
    )


@router.put("/sheet", response_model=TenantInfo)
def set_sheet(
    req: SetSheetRequest,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> TenantInfo:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede configurar la hoja",
        )

    sheet_id = extract_sheet_id(req.sheet)

    if not settings.has_supabase:  # demo: no persiste
        return _info(user.tenant_id, "Empresa demo", sheet_id, True)

    set_tenant_sheet(user.tenant_id, sheet_id)
    tenant = get_tenant(user.tenant_id)
    name = tenant["name"] if tenant else "Empresa"
    return _info(user.tenant_id, name, sheet_id, False)
