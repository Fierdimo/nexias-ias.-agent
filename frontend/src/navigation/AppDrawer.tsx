import {
  createDrawerNavigator,
  DrawerContentScrollView,
  DrawerItemList,
  type DrawerContentComponentProps,
} from "@react-navigation/drawer";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { useAuth } from "../auth/AuthContext";
import ChatScreen from "../screens/ChatScreen";
import ConfigScreen from "../screens/ConfigScreen";
import DashboardScreen from "../screens/DashboardScreen";

const Drawer = createDrawerNavigator();

function DrawerContent(props: DrawerContentComponentProps) {
  const { profile, logout } = useAuth();
  return (
    <DrawerContentScrollView {...props} contentContainerStyle={{ flex: 1 }}>
      <View style={styles.header}>
        <Text style={styles.brand}>Nexias</Text>
        <Text style={styles.email}>{profile.email}</Text>
      </View>
      <View style={{ flex: 1 }}>
        <DrawerItemList {...props} />
      </View>
      <TouchableOpacity style={styles.logout} onPress={logout}>
        <Text style={styles.logoutText}>Cerrar sesión</Text>
      </TouchableOpacity>
    </DrawerContentScrollView>
  );
}

export default function AppDrawer() {
  return (
    <Drawer.Navigator
      drawerContent={(props) => <DrawerContent {...props} />}
      screenOptions={{
        headerStyle: { backgroundColor: "#0f172a" },
        headerTintColor: "#fff",
        drawerActiveTintColor: "#2563eb",
      }}
    >
      <Drawer.Screen
        name="Chat"
        component={ChatScreen}
        options={{ title: "Asistente" }}
      />
      <Drawer.Screen
        name="Resumen"
        component={DashboardScreen}
        options={{ title: "Resumen" }}
      />
      <Drawer.Screen
        name="Configuración"
        component={ConfigScreen}
        options={{ title: "Configuración" }}
      />
    </Drawer.Navigator>
  );
}

const styles = StyleSheet.create({
  header: {
    backgroundColor: "#0f172a",
    padding: 20,
    paddingTop: 48,
    marginTop: -4,
  },
  brand: { color: "#fff", fontSize: 22, fontWeight: "800" },
  email: { color: "#94a3b8", fontSize: 12, marginTop: 4 },
  logout: {
    margin: 16,
    padding: 14,
    borderRadius: 12,
    backgroundColor: "#fee2e2",
    alignItems: "center",
  },
  logoutText: { color: "#dc2626", fontWeight: "700" },
});
