import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { ApiError, getTenant, setTenantSheet, type TenantInfo } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function ConfigScreen() {
  const { token, profile, logout } = useAuth();
  const [info, setInfo] = useState<TenantInfo | null>(null);
  const [sheet, setSheet] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const isAdmin = profile.role === "admin";

  async function refresh() {
    try {
      const t = await getTenant(token);
      setInfo(t);
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

  async function save() {
    setMsg(null);
    if (sheet.trim().length < 8) {
      setMsg("Pega el enlace o el ID de la hoja.");
      return;
    }
    setSaving(true);
    try {
      const t = await setTenantSheet(token, sheet.trim());
      setInfo(t);
      setSheet("");
      setMsg("✅ Hoja conectada. Ya puedes consultar tus datos reales.");
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

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={{ padding: 20, gap: 14 }}
    >
      <Text style={styles.title}>Google Sheets</Text>

      <View style={styles.card}>
        <Text style={styles.label}>Restaurante</Text>
        <Text style={styles.value}>{info?.name}</Text>
        <Text style={styles.label}>Estado</Text>
        <Text style={styles.value}>
          {info?.sheet_configured
            ? `Conectada (…${info.sheet_id?.slice(-6)})`
            : "Sin hoja conectada"}
        </Text>
        {info?.is_demo && (
          <Text style={styles.demo}>
            Modo demo: los cambios no se guardan.
          </Text>
        )}
      </View>

      {info?.service_account_email ? (
        <View style={styles.card}>
          <Text style={styles.label}>Comparte tu hoja con este email</Text>
          <Text selectable style={styles.email}>
            {info.service_account_email}
          </Text>
          <Text style={styles.hint}>
            En Google Sheets: Compartir → pega este email → permiso de Lector.
          </Text>
        </View>
      ) : (
        <Text style={styles.hint}>
          El backend aún no tiene credenciales de Google configuradas
          (GOOGLE_CREDENTIALS_PATH).
        </Text>
      )}

      {isAdmin ? (
        <View style={styles.card}>
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
            onPress={save}
            disabled={saving}
          >
            {saving ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.btnText}>Guardar</Text>
            )}
          </TouchableOpacity>
        </View>
      ) : (
        <Text style={styles.hint}>
          Solo el administrador puede cambiar la hoja.
        </Text>
      )}

      {msg && <Text style={styles.msg}>{msg}</Text>}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
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
    gap: 6,
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
    paddingVertical: 12,
    alignItems: "center",
    marginTop: 4,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: "#fff", fontWeight: "700" },
  msg: { fontSize: 14, color: "#0f172a" },
});
