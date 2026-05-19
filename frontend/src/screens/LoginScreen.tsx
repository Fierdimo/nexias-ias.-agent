import { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { login, signup } from "../api/client";
import type { Session } from "../auth/session";

type Props = { onAuth: (s: Session) => void };

export default function LoginScreen({ onAuth }: Props) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [company, setCompany] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isSignup = mode === "signup";

  async function submit() {
    setError(null);
    if (!email.trim() || !password) {
      setError("Email y contraseña son obligatorios.");
      return;
    }
    if (isSignup && company.trim().length < 2) {
      setError("Indica el nombre de la empresa.");
      return;
    }
    setLoading(true);
    try {
      const res = isSignup
        ? await signup(email.trim(), password, company.trim())
        : await login(email.trim(), password);
      onAuth({ token: res.access_token, profile: res.profile });
    } catch (e: any) {
      setError(e.message ?? "Error desconocido");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={styles.card}>
        <Text style={styles.brand}>Nexias</Text>
        <Text style={styles.subtitle}>
          {isSignup ? "Crea tu empresa" : "Inicia sesión"}
        </Text>

        <TextInput
          style={styles.input}
          placeholder="Email"
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />
        <TextInput
          style={styles.input}
          placeholder="Contraseña"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />
        {isSignup && (
          <TextInput
            style={styles.input}
            placeholder="Nombre de la empresa"
            value={company}
            onChangeText={setCompany}
          />
        )}

        {error && <Text style={styles.error}>{error}</Text>}

        <TouchableOpacity
          style={[styles.btn, loading && styles.btnDisabled]}
          onPress={submit}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.btnText}>
              {isSignup ? "Crear cuenta" : "Entrar"}
            </Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          onPress={() => {
            setMode(isSignup ? "login" : "signup");
            setError(null);
          }}
        >
          <Text style={styles.switch}>
            {isSignup
              ? "¿Ya tienes cuenta? Inicia sesión"
              : "¿Nuevo? Crea tu empresa"}
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
    justifyContent: "center",
    padding: 20,
  },
  card: { backgroundColor: "#fff", borderRadius: 18, padding: 24, gap: 12 },
  brand: {
    fontSize: 30,
    fontWeight: "800",
    color: "#0f172a",
    textAlign: "center",
  },
  subtitle: {
    fontSize: 15,
    color: "#475569",
    textAlign: "center",
    marginBottom: 6,
  },
  input: {
    backgroundColor: "#f1f5f9",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: "#cbd5e1",
  },
  error: { color: "#dc2626", fontSize: 13 },
  btn: {
    backgroundColor: "#2563eb",
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 4,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  switch: {
    color: "#2563eb",
    textAlign: "center",
    marginTop: 8,
    fontWeight: "600",
  },
});
