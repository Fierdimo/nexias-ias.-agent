# Nexias

Asistente que convierte los datos de **cualquier empresa** en informes
concisos en lenguaje natural (micro SaaS multi-tenant). Chat móvil que
responde sobre ventas, métricas y tendencias usando datos reales de
Google Sheets y un LLM (Kimi por defecto).

> **Modo demo:** sin credenciales el sistema funciona con un usuario y un
> dataset de muestra. Puedes probarlo todo en local antes de configurar nada.

## Estructura

```
backend/    FastAPI · Supabase · LLM · Sheets · analítica
frontend/   React Native / Expo (app móvil)
infra/      Dockerfile, docker-compose, esquema SQL de Supabase
docs/       ROADMAP.md y documentación
data/       documentos del cliente (no versionados)
```

## 1. Backend en local

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # opcional: edítalo para salir del modo demo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: http://localhost:8000/docs
- Estado/integraciones: http://localhost:8000/health
- Tests: `pytest -q`

`--host 0.0.0.0` es necesario para que el dispositivo físico alcance el backend.

## 2. Frontend (Expo) en dispositivo físico

```bash
cd frontend
npm install
cp .env.example .env
```

Edita `frontend/.env` con la **IP LAN de tu Mac** (no `localhost`):

```bash
ipconfig getifaddr en0          # ej: 192.168.1.50
# .env →  EXPO_PUBLIC_API_URL=http://192.168.1.50:8000
```

```bash
npm start
```

Escanea el QR con la app **Expo Go** en tu teléfono. El móvil y la Mac deben
estar en la **misma red Wi-Fi**.

## 3. Salir del modo demo (cuando quieras datos reales)

Edita `backend/.env`:

- **LLM (Kimi):** `LLM_PROVIDER=kimi`, `LLM_API_KEY=...`,
  `LLM_BASE_URL=https://api.moonshot.ai/v1` (o `.cn`).
  Para OpenAI: `LLM_PROVIDER=openai` y la base URL de OpenAI.
- **Supabase:** crea el proyecto, ejecuta `infra/supabase_schema.sql` en el
  SQL Editor y rellena `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`.
- **Google Sheets:** ver §6 (modelo: una hoja por empresa).

`/health` confirma qué integraciones están activas.

## 4. Autenticación (Fase 1)

El backend hace de proxy de Supabase Auth; la app solo habla con FastAPI.

**Requisito único:** ejecuta una vez [infra/supabase_schema.sql](infra/supabase_schema.sql)
en el SQL Editor de Supabase (crea `tenants`, `memberships`, `query_log` + RLS).

**Onboarding en una llamada** — `POST /auth/signup` crea el usuario (ya
confirmado, sin verificación por email), su empresa y la membresía de
admin, y devuelve la sesión:

```bash
curl -X POST http://localhost:8000/auth/signup -H 'Content-Type: application/json' \
  -d '{"email":"dueno@miempresa.com","password":"secreto123","company_name":"Mi Empresa"}'
```

Luego `POST /auth/login` con email/password devuelve `access_token`. La app:
guarda el token cifrado (`expo-secure-store`), lo manda como `Bearer` en
`/chat`, y al recibir `401` cierra sesión automáticamente.

> **Modo demo:** si Supabase no está configurado, `/auth/*` devuelve una
> sesión ficticia y la app funciona igual (útil para desarrollo offline).

## 5. Build nativo con EAS (development client)

Módulos como `expo-notifications` o `expo-audio` **no corren en Expo Go**:
requieren un *development build*. EAS ya está enlazado (`projectId` +
`owner` en [frontend/app.json](frontend/app.json), perfiles en
[frontend/eas.json](frontend/eas.json)).

El build corre en la **nube de Expo** (ligado a tu cuenta, consume cuota del
plan gratuito ~30/mes), por eso **lo ejecutas tú**:

```bash
cd frontend
npx eas-cli login                 # si no estás logueado
# Android (APK instalable, lo más rápido para probar):
npx eas-cli build --profile development --platform android
# iOS (requiere cuenta de Apple Developer para dispositivo físico):
npx eas-cli build --profile development --platform ios
```

Al terminar, instala el binario en el teléfono y arranca el dev server
apuntando al dev client (no Expo Go):

```bash
npx expo start --dev-client
```

Repite el build **solo cuando cambien dependencias nativas o `app.json`**
(plugins, permisos). El código JS/TS se actualiza por OTA sin rebuild.

Perfiles en `eas.json`: `development` (dev client), `preview` (APK interno
de QA), `production` (store, con autoincremento de versión).

## 6. Google Sheets por empresa (Fase 1)

Cada empresa (tenant) tiene su propia hoja. Un **único service account**
puede leer todas las hojas que estén compartidas con su email.

**Setup del service account (una sola vez):**
1. Google Cloud Console → crea un proyecto → habilita **Google Sheets API**.
2. IAM → Service Accounts → crea uno → Keys → **Add key (JSON)** → descarga.
3. Guarda el JSON fuera del repo y en `backend/.env`:
   `GOOGLE_CREDENTIALS_PATH=/ruta/al/service-account.json`
   (deja `GOOGLE_SHEET_ID` vacío: ahora la hoja es por tenant).
4. Reinicia el backend. `GET /tenant` ya devuelve el email del service
   account (`client_email` del JSON).

**Conectar la hoja de una empresa (desde la app, sin SQL):**
- Drawer → **Configuración** (solo rol `admin`).
- Comparte tu Google Sheet con el email del service account (permiso Lector).
- Pega el **enlace o ID** de la hoja y guarda. Queda en `tenants.sheet_id`.

Hoja esperada (primera fila = encabezados, primera pestaña):
`fecha | producto | categoria | cantidad | ingresos`

Si la hoja no está compartida o el ID es inválido, el chat responde con un
aviso claro (e indica con qué email compartirla) en vez de fallar.

## 7. "Entrar con Google" + Picker (Fase 1, recomendado)

Sin fricción: el usuario inicia sesión con Google y elige sus hojas en el
selector oficial. Scope **`drive.file`** → la app solo ve lo elegido →
**sin evaluación CASA, gratis**. Para piloto, deja la app OAuth en
"Testing" (hasta 100 usuarios, sin verificación).

**Google Cloud (una sola vez):**
1. APIs y servicios → Habilitar: **Google Sheets API**, **Google Drive
   API**, **Google Picker API**.
2. Pantalla de consentimiento OAuth → External → modo Testing → añade tus
   emails de prueba. Scopes: `openid`, `email`, `profile`,
   `.../auth/drive.file`.
3. Credenciales (crea TRES OAuth clients en el mismo proyecto):
   - **Web** → *Client ID* + *Client secret*. JS origins autorizados: la
     URL del backend (para la página del Picker). Este es el que el
     backend usa para canjear el `serverAuthCode`.
   - **iOS** (si vas a probar en iPhone) → *Client ID* + *iOS URL scheme*
     (formato `com.googleusercontent.apps.<id>`). Bundle ID
     `com.nexias.app`.
   - **Android** (si vas a probar en Android) → package `com.nexias.app`
     + huella SHA-1 del keystore del dev build
     (`eas credentials -p android` te la da).
   - **API key** (restringida a Picker API).
4. Anota el **número de proyecto** (Configuración del proyecto) = appId.
5. En `backend/.env`: `GOOGLE_OAUTH_CLIENT_ID` (el del Web),
   `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_API_KEY`,
   `GOOGLE_PROJECT_NUMBER`, y `TOKEN_ENC_KEY`
   (`python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"`).
   Reinicia el backend.
6. En `frontend/.env`: `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` (mismo Web del
   paso 5) y, si usas iPhone, `EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID`.
7. En `frontend/app.json` reemplaza `iosUrlScheme` del plugin
   `@react-native-google-signin/google-signin` por el de tu OAuth iOS
   (lo dice como `com.googleusercontent.apps.<id>`).
8. **Rebuild del dev client EAS** (google-signin es nativo, no corre en
   Expo Go ni en el dev client viejo):
   `npx eas-cli build --profile development --platform android` (o iOS).
   Reinstala el binario en el teléfono.

**Flujo (en la app):** Drawer → Configuración → "Conectar con Google" →
login nativo → backend canjea el `serverAuthCode` y guarda el refresh
token cifrado → "Elegir hojas" abre el Picker en un WebView → al
seleccionar, las hojas quedan en `data_sources`. El chat usa esas hojas
vía OAuth (prioridad sobre el service account).

`GET /health` y `GET /google/status` confirman si está configurado.

## 8. Esquema flexible (Fase 1.5)

Nexias entiende **cualquier hoja**, no solo el modelo `fecha|producto|…`.
Al elegir un archivo en el Picker, el backend:

1. **Perfila** la hoja: detecta tipos por columna (fecha / número / texto),
   muestras y conteos. Determinista, sin IA.
2. **Asigna roles** a cada columna (`date`, `revenue`, `quantity`,
   `category`, `id`, `ignore`). Heurística por palabras clave + tipos
   como base; si el LLM está configurado, refina con JSON estricto.
3. **Guarda el esquema** en `data_sources.schema_json` (1 sola vez por
   hoja). El chat usa ese esquema para calcular métricas dinámicas
   (totales por columna revenue, top por categoría, variación semanal)
   con **pandas → anti-alucinación**.

En Configuración cada hoja muestra resumen, chips de rol y un botón
**Re-analizar** (`POST /google/sources/{id}/analyze`) para refrescar el
esquema si la hoja cambia.

## Arquitectura clave (anti-alucinación)

```
pregunta → carga ventas (Sheets) → métricas con pandas → LLM redacta → respuesta
                                    └─ números exactos, el LLM NO los inventa
```

Ver [docs/ROADMAP.md](docs/ROADMAP.md) para fases y decisiones.
