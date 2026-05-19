import { StyleSheet, Text, View } from "react-native";

import { useAuth } from "../auth/AuthContext";

export default function DashboardScreen() {
  const { profile } = useAuth();
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Resumen</Text>
      <Text style={styles.meta}>Restaurante: {profile.tenant_id}</Text>
      <Text style={styles.meta}>Rol: {profile.role}</Text>
      <Text style={styles.soon}>
        📊 Próximamente: métricas y gráficos de ventas (Fase 1 del roadmap).
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f8fafc",
    padding: 24,
    gap: 8,
  },
  title: { fontSize: 22, fontWeight: "800", color: "#0f172a" },
  meta: { color: "#475569" },
  soon: { marginTop: 16, color: "#64748b", fontStyle: "italic" },
});
