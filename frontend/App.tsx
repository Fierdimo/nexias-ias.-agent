// IMPORTANTE: este import debe ser el PRIMERO de toda la app (requisito de
// react-native-gesture-handler para que el drawer y los gestos funcionen).
import "react-native-gesture-handler";

import { NavigationContainer } from "@react-navigation/native";
import { StatusBar } from "expo-status-bar";
import { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { ApiError, getProfile } from "./src/api/client";
import { AuthProvider } from "./src/auth/AuthContext";
import {
  clearSession,
  loadSession,
  saveSession,
  type Session,
} from "./src/auth/session";
import AppDrawer from "./src/navigation/AppDrawer";
import LoginScreen from "./src/screens/LoginScreen";

export default function App() {
  const [booting, setBooting] = useState(true);
  const [session, setSession] = useState<Session | null>(null);

  // Al arrancar: restaurar sesión guardada y validarla contra el backend.
  useEffect(() => {
    (async () => {
      const saved = await loadSession();
      if (saved) {
        try {
          await getProfile(saved.token);
          setSession(saved);
        } catch (e) {
          if (e instanceof ApiError && e.status === 401) {
            await clearSession();
          }
        }
      }
      setBooting(false);
    })();
  }, []);

  async function handleAuth(s: Session) {
    await saveSession(s);
    setSession(s);
  }

  async function handleLogout() {
    await clearSession();
    setSession(null);
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <StatusBar style="light" />
        {booting ? (
          <View style={styles.splash}>
            <ActivityIndicator color="#fff" size="large" />
          </View>
        ) : session ? (
          <AuthProvider
            value={{
              token: session.token,
              profile: session.profile,
              logout: handleLogout,
            }}
          >
            <NavigationContainer>
              <AppDrawer />
            </NavigationContainer>
          </AuthProvider>
        ) : (
          <LoginScreen onAuth={handleAuth} />
        )}
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  splash: {
    flex: 1,
    backgroundColor: "#0f172a",
    alignItems: "center",
    justifyContent: "center",
  },
});
