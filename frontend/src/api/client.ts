/**
 * Cliente del backend Nexias.
 *
 * IMPORTANTE para DISPOSITIVO FÍSICO:
 * "localhost" apunta al teléfono, no a tu Mac. Usa la IP LAN en
 * frontend/.env →  EXPO_PUBLIC_API_URL=http://192.168.1.9:8000
 * (IP con `ipconfig getifaddr en0` en macOS).
 */
const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export type Profile = {
  user_id: string;
  email: string;
  tenant_id: string;
  role: string;
};

export type AuthResponse = {
  access_token: string;
  refresh_token: string | null;
  profile: Profile;
  is_demo: boolean;
};

export type ChatResponse = {
  answer: string;
  tenant_id: string;
  is_demo: boolean;
  metrics: Record<string, unknown>;
};

export type TenantInfo = {
  tenant_id: string;
  name: string;
  sheet_id: string | null;
  sheet_configured: boolean;
  service_account_email: string | null;
  is_demo: boolean;
};

export type PickedFile = {
  id: string;
  name?: string;
  mimeType?: string;
  schema_summary?: string | null;
  schema_source?: "ai" | "heuristic" | null;
  schema_columns?: { name: string; role: string }[] | null;
};

export type GoogleStatus = {
  oauth_configured: boolean;
  connected: boolean;
  email: string | null;
  sources: PickedFile[];
  is_demo: boolean;
};

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; token?: string } = {}
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method: options.method ?? "GET",
      headers: {
        "Content-Type": "application/json",
        ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    // fetch lanza TypeError cuando no hay red / backend inalcanzable.
    throw new ApiError(
      0,
      `No se pudo conectar con el servidor (${BASE_URL}). ` +
        `Verifica que el backend esté corriendo y la IP en .env.`
    );
  }

  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = String(data.detail);
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export function login(email: string, password: string) {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export function signup(
  email: string,
  password: string,
  companyName: string
) {
  return request<AuthResponse>("/auth/signup", {
    method: "POST",
    body: { email, password, company_name: companyName },
  });
}

export function getProfile(token: string) {
  return request<Profile>("/auth/me", { token });
}

export function sendChat(message: string, token: string) {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: { message },
    token,
  });
}

export function getTenant(token: string) {
  return request<TenantInfo>("/tenant", { token });
}

export function setTenantSheet(token: string, sheet: string) {
  return request<TenantInfo>("/tenant/sheet", {
    method: "PUT",
    body: { sheet },
    token,
  });
}

export function googleStatus(token: string) {
  return request<GoogleStatus>("/google/status", { token });
}

export function googleConnect(token: string, serverAuthCode: string) {
  return request<GoogleStatus>("/google/connect", {
    method: "POST",
    body: { server_auth_code: serverAuthCode },
    token,
  });
}

export function googleSetSources(token: string, files: PickedFile[]) {
  return request<GoogleStatus>("/google/sources", {
    method: "POST",
    body: { files },
    token,
  });
}

export function reanalyzeSource(token: string, fileId: string) {
  return request<GoogleStatus>(
    `/google/sources/${encodeURIComponent(fileId)}/analyze`,
    { method: "POST", token }
  );
}

/** URL del Picker para abrir en un WebView (auth por query param). */
export function pickerUrl(token: string) {
  return `${BASE_URL}/google/picker?t=${encodeURIComponent(token)}`;
}

export { BASE_URL };
