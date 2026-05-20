-- Esquema mínimo multi-tenant para Supabase.
-- Ejecútalo en: Supabase Studio > SQL Editor.

-- Restaurantes (tenants)
-- sheet_id: ID de la Google Sheet de ESE restaurante (datos de ventas).
create table if not exists tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  sheet_id text,
  created_at timestamptz default now()
);

-- Idempotente: si ya creaste la tabla antes, añade la columna.
alter table tenants add column if not exists sheet_id text;

-- Relación usuario <-> restaurante con rol.
-- user_id referencia auth.users (Supabase Auth).
create table if not exists memberships (
  user_id uuid not null references auth.users (id) on delete cascade,
  tenant_id uuid not null references tenants (id) on delete cascade,
  role text not null check (role in ('admin', 'gerente', 'analista')),
  primary key (user_id, tenant_id)
);

-- Auditoría de consultas.
create table if not exists query_log (
  id bigint generated always as identity primary key,
  tenant_id uuid not null references tenants (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  question text not null,
  created_at timestamptz default now()
);

create index if not exists query_log_tenant_idx on query_log (tenant_id, created_at desc);

-- RLS: cada usuario solo ve filas de su tenant.
alter table memberships enable row level security;
alter table query_log enable row level security;

-- Idempotente: Postgres no soporta CREATE POLICY IF NOT EXISTS.
drop policy if exists "miembro ve su membership" on memberships;
create policy "miembro ve su membership"
  on memberships for select
  using (user_id = auth.uid());

drop policy if exists "miembro ve logs de su tenant" on query_log;
create policy "miembro ve logs de su tenant"
  on query_log for select
  using (
    tenant_id in (select tenant_id from memberships where user_id = auth.uid())
  );

-- ---------------------------------------------------------------------------
-- Google OAuth por restaurante ("Entrar con Google" + Picker, scope drive.file)
-- ---------------------------------------------------------------------------

-- Refresh token de Google cifrado (Fernet) por tenant. El backend lo usa
-- para leer las hojas elegidas, incluso en reportes sin el usuario presente.
create table if not exists google_accounts (
  tenant_id uuid primary key references tenants (id) on delete cascade,
  google_email text,
  refresh_token_enc text not null,
  access_token_enc text,
  access_expiry timestamptz,
  updated_at timestamptz default now()
);

-- Archivos/carpetas que el usuario eligió en el Google Picker.
create table if not exists data_sources (
  id bigint generated always as identity primary key,
  tenant_id uuid not null references tenants (id) on delete cascade,
  file_id text not null,
  name text,
  mime_type text,
  -- Esquema inferido (perfil + roles por columna + resumen).
  -- jsonb para poder consultar y para que crezca sin migraciones.
  schema_json jsonb,
  schema_updated_at timestamptz,
  created_at timestamptz default now(),
  unique (tenant_id, file_id)
);

-- Idempotente para bases ya creadas.
alter table data_sources add column if not exists schema_json jsonb;
alter table data_sources add column if not exists schema_updated_at timestamptz;

create index if not exists data_sources_tenant_idx on data_sources (tenant_id);

-- Secretos: nadie los lee vía API anónima (solo el backend con service key,
-- que ignora RLS). Habilitamos RLS sin políticas de SELECT = acceso negado.
alter table google_accounts enable row level security;
alter table data_sources enable row level security;
