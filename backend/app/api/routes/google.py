"""Login con Google + Google Picker (scope drive.file) por tenant.

- POST /google/connect : el móvil manda el server auth code; lo cambiamos
  por refresh token (cifrado) para leer las hojas elegidas.
- GET  /google/status  : estado de conexión + archivos seleccionados.
- POST /google/sources : guarda lo que el usuario eligió en el Picker.
- GET  /google/picker  : página HTML que embebe el Google Picker (se abre
  en un WebView del móvil). Autentica por query param porque un WebView
  GET no manda headers.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse

from app.config import Settings, get_settings
from app.core.security import (
    CurrentUser,
    get_current_user,
    resolve_user_from_token,
)
from app.schemas.google import (
    ConnectRequest,
    GoogleStatus,
    PickedFile,
    SourcesRequest,
)
from app.services.data_sources import (
    SPREADSHEET_MIME,
    list_sources,
    replace_sources,
)
from app.services.google_oauth import (
    exchange_code,
    get_account,
    get_valid_access_token,
    save_account,
)
from app.services.sheet_analyzer import analyze_source

router = APIRouter(prefix="/google", tags=["google"])


def _require_admin(user: CurrentUser) -> None:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede gestionar la conexión",
        )


@router.get("/status", response_model=GoogleStatus)
def status_(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> GoogleStatus:
    if not settings.has_google_oauth:
        return GoogleStatus(
            oauth_configured=False, connected=False, is_demo=not settings.has_supabase
        )
    acct = get_account(user.tenant_id)
    sources = []
    for s in list_sources(user.tenant_id):
        schema = s.get("schema_json") or {}
        sources.append(
            PickedFile(
                id=s["file_id"],
                name=s.get("name"),
                mimeType=s.get("mime_type"),
                schema_summary=schema.get("summary"),
                schema_source=schema.get("source"),
                schema_columns=schema.get("columns"),
            )
        )
    return GoogleStatus(
        oauth_configured=True,
        connected=acct is not None,
        email=acct.get("google_email") if acct else None,
        sources=sources,
        is_demo=not settings.has_supabase,
    )


@router.post("/connect", response_model=GoogleStatus)
def connect(
    req: ConnectRequest,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> GoogleStatus:
    _require_admin(user)
    if not settings.has_google_oauth:
        raise HTTPException(
            status_code=503, detail="Google OAuth no está configurado en el backend"
        )
    try:
        tok = exchange_code(
            req.server_auth_code, req.redirect_uri, req.code_verifier
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Fallo el intercambio: {exc}")

    save_account(
        user.tenant_id,
        tok["email"],
        tok["refresh_token"],
        tok.get("access_token"),
        tok.get("expires_in", 3600),
    )
    return status_(user=user, settings=settings)


@router.post("/sources", response_model=GoogleStatus)
def set_sources(
    req: SourcesRequest,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> GoogleStatus:
    _require_admin(user)
    replace_sources(
        user.tenant_id, [f.model_dump() for f in req.files]
    )
    # Inferencia automática del esquema para cada spreadsheet elegida.
    # Best-effort: si falla una hoja, las demás siguen.
    for f in req.files:
        if f.mimeType == SPREADSHEET_MIME:
            try:
                analyze_source(user.tenant_id, f.id, f.name)
            except Exception:
                pass
    return status_(user=user, settings=settings)


@router.post("/sources/{file_id}/analyze", response_model=GoogleStatus)
def reanalyze(
    file_id: str,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> GoogleStatus:
    """Re-analiza una hoja existente para refrescar su esquema."""
    _require_admin(user)
    analyze_source(user.tenant_id, file_id)
    return status_(user=user, settings=settings)


@router.get("/picker", response_class=HTMLResponse)
def picker(
    t: str,
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    """HTML del Picker. Se abre en un WebView; `t` = token Supabase."""
    user = resolve_user_from_token(t, settings)
    if not settings.has_google_oauth:
        return HTMLResponse("<h3>Google no está configurado en el backend.</h3>")

    access_token = get_valid_access_token(user.tenant_id)
    if not access_token:
        return HTMLResponse(
            "<h3>Conecta tu cuenta de Google antes de elegir archivos.</h3>"
        )

    html = (
        _PICKER_HTML.replace("__TOKEN__", access_token)
        .replace("__APIKEY__", settings.google_api_key)
        .replace("__APPID__", settings.google_project_number)
    )
    return HTMLResponse(html)


# El Picker es un widget web de Google; lo embebemos en un WebView del móvil.
# Al elegir, manda los archivos al app vía ReactNativeWebView.postMessage.
_PICKER_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Elegir archivos</title></head>
<body style="font-family:sans-serif;padding:24px;background:#0f172a;color:#fff">
<p>Cargando selector de Google…</p>
<script src="https://apis.google.com/js/api.js"></script>
<script>
function send(payload){
  if (window.ReactNativeWebView) {
    window.ReactNativeWebView.postMessage(JSON.stringify(payload));
  }
}
function onPicked(data){
  if (data.action === google.picker.Action.PICKED) {
    var files = (data.docs || []).map(function(d){
      return { id: d.id, name: d.name, mimeType: d.mimeType };
    });
    send({ status: "picked", files: files });
  } else if (data.action === google.picker.Action.CANCEL) {
    send({ status: "cancel" });
  }
}
function createPicker(){
  var sheets = new google.picker.DocsView(google.picker.ViewId.SPREADSHEETS)
    .setIncludeFolders(true).setSelectFolderEnabled(true);
  var picker = new google.picker.PickerBuilder()
    .addView(sheets)
    .enableFeature(google.picker.Feature.MULTISELECT_ENABLED)
    .setOAuthToken("__TOKEN__")
    .setDeveloperKey("__APIKEY__")
    .setAppId("__APPID__")
    .setCallback(onPicked)
    .build();
  picker.setVisible(true);
}
gapi.load("picker", { callback: createPicker });
</script></body></html>"""
