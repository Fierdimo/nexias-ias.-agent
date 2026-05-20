# Roadmap — Nexias

Asistente que transforma datos de **cualquier empresa** en informes
concisos en lenguaje natural. Micro SaaS multi-tenant con marca propia.
Arquitectura modular: el éxito depende de la capa de **datos + retrieval
+ herramientas externas**, no del modelo.

## Estado actual (MVP base — implementado)

- [x] Backend FastAPI con estructura modular
- [x] Capa de abstracción LLM (Kimi por defecto, intercambiable con OpenAI/Claude)
- [x] Lectura de ventas desde Google Sheets (+ dataset de muestra en demo)
- [x] Métricas calculadas con pandas **fuera del LLM** (anti-alucinación)
- [x] Endpoint `/chat`: datos → cálculo → LLM redacta
- [x] Auth Supabase + multi-tenant + auditoría de consultas
- [x] App móvil Expo (React Native) con chat funcional
- [x] Modo demo: corre sin credenciales para desarrollo local
- [x] Smoke tests verdes

## Fase 1 — Producto vendible (en curso)

- [x] Pantalla de login/signup en la app (backend proxy de Supabase Auth)
- [x] Onboarding en una llamada: signup crea usuario + empresa + membresía
- [x] Persistir token de sesión cifrado en el dispositivo (expo-secure-store)
- [x] Gate de auth + logout + 401 → cierre de sesión automático
- [x] Manejo de errores (red caída, credenciales, sesión expirada)
- [x] Cada tenant lee su propia Google Sheet (columna `sheet_id`,
      endpoints `/tenant`, pantalla Configuración, 1 service account)
- [x] Navegación con Drawer (Chat / Resumen / Configuración)
- [~] "Entrar con Google" + Picker (scope drive.file, sin CASA):
      backend listo (OAuth, refresh cifrado, data_sources, /google/*);
      falta frontend (botón OAuth + Picker en WebView)
- [ ] Selector de empresa si el usuario pertenece a varias
- [ ] Memoria de conversación (historial + resumen periódico)
- [ ] Dashboard básico de métricas (no solo chat)

## Fase 1.5 — Esquema flexible (datos de cualquier empresa)

Hoy la analítica asume columnas fijas
(`fecha|producto|categoria|cantidad|ingresos`). Para servir a cualquier
empresa, las columnas deben ser libres y entendidas por IA.

- [x] Perfilado automático de la hoja (tipos, muestras, conteos)
- [x] Asignación de roles por columna: heurística + LLM (JSON estricto)
- [x] Esquema persistido por hoja (`data_sources.schema_json`)
- [x] Inferencia automática al seleccionar archivos en el Picker
- [x] Endpoint `POST /google/sources/{id}/analyze` para re-analizar
- [x] Métricas dinámicas por roles (`build_metrics_dynamic`)
- [x] Cálculos deterministas (pandas) sobre columnas detectadas → anti-alucinación
- [x] UI: tarjeta por hoja con resumen, chips de rol y botón Re-analizar
- [ ] Permitir al usuario editar manualmente los roles asignados
- [ ] Dataset de muestra genérico (no específico de un sector)
- [ ] Soporte para múltiples hojas combinadas en una consulta

## Fase 2 — IA sobre documentos (RAG completo)

- [ ] Ingesta de PDFs/Excel de `data/documents`
- [ ] Chunking + embeddings + vector store (pgvector en Supabase)
- [ ] Recuperación semántica por consulta (solo contexto relevante)
- [ ] Citas: indicar de qué documento salió cada dato
- [ ] Evaluación de alucinaciones con set de preguntas de prueba

## Fase 3 — Escala y monetización

- [ ] Onboarding self-service de nuevas empresas
- [ ] Planes/límites de uso por tenant
- [ ] Métricas de costo de LLM por cliente
- [ ] Comparativas y proyecciones avanzadas
- [ ] Síntesis de voz (respuestas habladas)
- [ ] Canales adicionales (WhatsApp/Telegram) reusando el mismo backend

## Decisiones de arquitectura

| Tema | Decisión | Razón |
|---|---|---|
| Frontend | React Native / Expo | Una base de código, MVP rápido, costo bajo |
| Backend | FastAPI (Python) | Ecosistema de datos/IA, async, simple |
| DB + Auth | Supabase | Auth + Postgres + pgvector + RLS gestionado |
| LLM | Kimi vía capa de abstracción | Tokens baratos; intercambiable sin reescribir |
| Anti-alucinación | Cálculos en pandas, no en el LLM | Los números deben ser exactos |
| Datos | Google Sheets primero | Fuente que el cliente ya usa |

## Costos estimados

- MVP pequeño: **$30–80 / mes** (Supabase free/pro, Kimi con RAG, hosting básico)
- Escala moderada: **$100–250 / mes**

## Riesgos y mitigaciones

- **Alucinaciones** → métricas deterministas + RAG con citas + temperatura baja
- **Contexto largo** → resúmenes de sesión + retrieval, no prompt gigante
- **Lock-in de LLM** → capa de abstracción ya implementada
- **Privacidad multi-tenant** → RLS en Supabase + filtro por `tenant_id` en backend
