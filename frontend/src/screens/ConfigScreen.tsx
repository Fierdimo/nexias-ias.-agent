import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { WebView, type WebViewMessageEvent } from "react-native-webview";

import {
  ApiError,
  type GoogleStatus,
  type TenantInfo,
  getTenant,
  googleConnect,
  googleSetSources,
  googleStatus as fetchGoogleStatus,
  pickerUrl,
  reanalyzeSource,
  setTenantSheet,
} from "../api/client";
import {
  GoogleCancelled,
  googleConfigured,
  signInForServerCode,
} from "../auth/google";
import { useAuth } from "../auth/AuthContext";

export default function ConfigScreen() {
  const { token, profile, logout } = useAuth();
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [gstatus, setGstatus] = useState<GoogleStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [gBusy, setGBusy] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [sheet, setSheet] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const isAdmin = profile.role === "admin";

  async function refresh() {
    try {
      const [t, g] = await Promise.all([
        getTenant(token),
        fetchGoogleStatus(token),
      ]);
      setTenant(t);
      setGstatus(g);
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 401) return logout();
      setMsg(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function connectGoogle() {
    setMsg(null);
    setGBusy(true);
    try {
      const code = await signInForServerCode();
      const g = await googleConnect(token, code);
      setGstatus(g);
      setMsg("✅ Cuenta de Google conectada. Ahora elige tus hojas.");
    } catch (e: any) {
      if (e instanceof GoogleCancelled) return;
      if (e instanceof ApiError && e.status === 401) return logout();
      setMsg(`⚠️ ${e.message ?? "No se pudo conectar con Google"}`);
    } finally {
      setGBusy(false);
    }
  }

  async function onReanalyze(fileId: string) {
    setMsg(null);
    setGBusy(true);
    try {
      const g = await reanalyzeSource(token, fileId);
      setGstatus(g);
      setMsg("✅ Esquema actualizado.");
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 401) return logout();
      setMsg(`⚠️ ${e.message}`);
    } finally {
      setGBusy(false);
    }
  }

  async function onPickerMessage(ev: WebViewMessageEvent) {
    let payload: any;
    try {
      payload = JSON.parse(ev.nativeEvent.data);
    } catch {
      return;
    }
    if (payload?.status === "cancel") {
      setPickerOpen(false);
      return;
    }
    if (payload?.status !== "picked") return;
    setPickerOpen(false);
    setGBusy(true);
    try {
      const g = await googleSetSources(token, payload.files ?? []);
      setGstatus(g);
      setMsg(`✅ ${payload.files?.length ?? 0} archivo(s) conectado(s).`);
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 401) return logout();
      setMsg(`⚠️ ${e.message}`);
    } finally {
      setGBusy(false);
    }
  }

  async function saveServiceAccountSheet() {
    setMsg(null);
    if (sheet.trim().length < 8) {
      setMsg("Pega el enlace o el ID de la hoja.");
      return;
    }
    setSaving(true);
    try {
      const t = await setTenantSheet(token, sheet.trim());
      setTenant(t);
      setSheet("");
      setMsg("✅ Hoja conectada (modo service account).");
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 401) return logout();
      setMsg(`⚠️ ${e.message}`);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  const oauthReady = googleConfigured && gstatus?.oauth_configured;

  return (
    <>
      <ScrollView
        style={styles.container}
        contentContainerStyle={{ padding: 20, gap: 14 }}
      >
        <Text style={styles.title}>Datos de la empresa</Text>

        <View style={styles.card}>
          <Text style={styles.label}>Empresa</Text>
          <Text style={styles.value}>{tenant?.name}</Text>
          {tenant?.is_demo && (
            <Text style={styles.demo}>
              Modo demo: los cambios no se guardan en una base real.
            </Text>
          )}
        </View>

        {/* --- Camino recomendado: Google --- */}
        <View style={styles.card}>
          <Text style={styles.label}>Conectar con Google</Text>

          {!googleConfigured && (
            <Text style={styles.hint}>
              Frontend sin configurar: define EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID
              en frontend/.env y reconstruye el dev build.
            </Text>
          )}
          {googleConfigured && !gstatus?.oauth_configured && (
            <Text style={styles.hint}>
              Backend sin configurar: completa GOOGLE_OAUTH_* y TOKEN_ENC_KEY
              en backend/.env (ver README §7).
            </Text>
          )}

          {oauthReady && !gstatus?.connected && isAdmin && (
            <TouchableOpacity
              style={[styles.btn, gBusy && styles.btnDisabled]}
              onPress={connectGoogle}
              disabled={gBusy}
              accessibilityLabel="Conectar con Google"
            >
              {gBusy ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.btnText}>Conectar con Google</Text>
              )}
            </TouchableOpacity>
          )}

          {oauthReady && gstatus?.connected && (
            <>
              <Text style={styles.value}>{gstatus.email}</Text>
              <Text style={styles.label}>Hojas conectadas</Text>
              {gstatus.sources.length === 0 ? (
                <Text style={styles.hint}>
                  Aún no has elegido archivos.
                </Text>
              ) : (
                gstatus.sources.map((s) => (
                  <View key={s.id} style={styles.sourceCard}>
                    <Text style={styles.sourceName} numberOfLines={1}>
                      {s.name ?? s.id}
                    </Text>
                    {s.schema_summary ? (
                      <Text style={styles.sourceSummary}>
                        {s.schema_summary}
                      </Text>
                    ) : (
                      <Text style={styles.hint}>
                        Aún no analizado. Re-analiza para que la IA entienda
                        las columnas.
                      </Text>
                    )}
                    {s.schema_columns && s.schema_columns.length > 0 && (
                      <View style={styles.chipsRow}>
                        {s.schema_columns
                          .filter((c) => c.role !== "ignore")
                          .map((c) => (
                            <View
                              key={c.name}
                              style={[
                                styles.chip,
                                roleColor(c.role),
                              ]}
                            >
                              <Text style={styles.chipText} numberOfLines={1}>
                                {c.name}: {c.role}
                              </Text>
                            </View>
                          ))}
                      </View>
                    )}
                    {s.schema_source && (
                      <Text style={styles.hint}>
                        Esquema por{" "}
                        {s.schema_source === "ai" ? "IA" : "reglas"}
                      </Text>
                    )}
                    {isAdmin && (
                      <TouchableOpacity
                        onPress={() => onReanalyze(s.id)}
                        disabled={gBusy}
                      >
                        <Text style={styles.link}>Re-analizar</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                ))
              )}
              {isAdmin && (
                <TouchableOpacity
                  style={[styles.btn, gBusy && styles.btnDisabled]}
                  onPress={() => setPickerOpen(true)}
                  disabled={gBusy}
                >
                  <Text style={styles.btnText}>
                    {gstatus.sources.length === 0
                      ? "Elegir hojas"
                      : "Cambiar selección"}
                  </Text>
                </TouchableOpacity>
              )}
            </>
          )}

          {!isAdmin && (
            <Text style={styles.hint}>
              Solo el administrador puede gestionar la conexión.
            </Text>
          )}
        </View>

        {/* --- Avanzado: service account --- */}
        <TouchableOpacity onPress={() => setShowAdvanced((v) => !v)}>
          <Text style={styles.link}>
            {showAdvanced ? "Ocultar" : "Mostrar"} opciones avanzadas
            (compartir hoja manualmente)
          </Text>
        </TouchableOpacity>

        {showAdvanced && (
          <View style={styles.card}>
            <Text style={styles.label}>Hoja actual (service account)</Text>
            <Text style={styles.value}>
              {tenant?.sheet_configured
                ? `Conectada (…${tenant.sheet_id?.slice(-6)})`
                : "Sin hoja conectada"}
            </Text>
            {tenant?.service_account_email && (
              <>
                <Text style={styles.label}>
                  Comparte tu hoja con este email
                </Text>
                <Text selectable style={styles.email}>
                  {tenant.service_account_email}
                </Text>
                <Text style={styles.hint}>
                  Compartir → pega este email → permiso de Lector.
                </Text>
              </>
            )}
            {isAdmin && (
              <>
                <Text style={styles.label}>Enlace o ID de la hoja</Text>
                <TextInput
                  style={styles.input}
                  placeholder="https://docs.google.com/spreadsheets/d/…"
                  autoCapitalize="none"
                  value={sheet}
                  onChangeText={setSheet}
                />
                <TouchableOpacity
                  style={[styles.btn, saving && styles.btnDisabled]}
                  onPress={saveServiceAccountSheet}
                  disabled={saving}
                >
                  {saving ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.btnText}>Guardar</Text>
                  )}
                </TouchableOpacity>
              </>
            )}
          </View>
        )}

        {msg && <Text style={styles.msg}>{msg}</Text>}
      </ScrollView>

      <Modal
        visible={pickerOpen}
        animationType="slide"
        onRequestClose={() => setPickerOpen(false)}
      >
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Elegir hojas</Text>
          <TouchableOpacity onPress={() => setPickerOpen(false)} hitSlop={10}>
            <Text style={styles.modalClose}>Cerrar</Text>
          </TouchableOpacity>
        </View>
        <WebView
          source={{ uri: pickerUrl(token) }}
          onMessage={onPickerMessage}
          javaScriptEnabled
          domStorageEnabled
        />
      </Modal>
    </>
  );
}

function roleColor(role: string) {
  switch (role) {
    case "date":
      return { backgroundColor: "#dbeafe" };
    case "revenue":
      return { backgroundColor: "#dcfce7" };
    case "quantity":
      return { backgroundColor: "#fef3c7" };
    case "category":
      return { backgroundColor: "#ede9fe" };
    case "id":
      return { backgroundColor: "#f1f5f9" };
    default:
      return { backgroundColor: "#f1f5f9" };
  }
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  sourceCard: {
    backgroundColor: "#f8fafc",
    borderRadius: 10,
    padding: 12,
    marginTop: 4,
    gap: 6,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  sourceName: { fontSize: 14, fontWeight: "700", color: "#0f172a" },
  sourceSummary: { fontSize: 13, color: "#334155" },
  chipsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginTop: 4,
  },
  chip: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    maxWidth: "100%",
  },
  chipText: { fontSize: 11, color: "#0f172a" },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#f8fafc",
  },
  title: { fontSize: 22, fontWeight: "800", color: "#0f172a" },
  card: {
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 16,
    gap: 8,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  label: {
    fontSize: 12,
    color: "#64748b",
    marginTop: 4,
    textTransform: "uppercase",
  },
  value: { fontSize: 15, color: "#0f172a", fontWeight: "600" },
  email: { fontSize: 14, color: "#2563eb", fontWeight: "600" },
  hint: { fontSize: 13, color: "#64748b" },
  demo: { fontSize: 13, color: "#b45309", marginTop: 4 },
  source: { fontSize: 14, color: "#0f172a" },
  link: { color: "#2563eb", fontWeight: "600", marginTop: 4 },
  input: {
    backgroundColor: "#f1f5f9",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: "#cbd5e1",
  },
  btn: {
    backgroundColor: "#2563eb",
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 6,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  msg: { fontSize: 14, color: "#0f172a" },
  modalHeader: {
    backgroundColor: "#0f172a",
    paddingTop: 56,
    paddingHorizontal: 16,
    paddingBottom: 12,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  modalTitle: { color: "#fff", fontSize: 18, fontWeight: "700" },
  modalClose: { color: "#93c5fd", fontWeight: "600" },
});
