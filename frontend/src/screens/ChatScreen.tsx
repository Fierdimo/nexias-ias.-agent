import { useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { ApiError, sendChat } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Msg = { id: string; role: "user" | "bot"; text: string };

export default function ChatScreen() {
  const { token, logout } = useAuth();
  const [messages, setMessages] = useState<Msg[]>([
    {
      id: "0",
      role: "bot",
      text: "Hola 👋 Pregúntame sobre ventas, productos o tendencias del restaurante.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSend() {
    const text = input.trim();
    if (!text || loading) return;
    const userMsg: Msg = { id: Date.now() + "u", role: "user", text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await sendChat(text, token);
      setMessages((m) => [
        ...m,
        { id: Date.now() + "b", role: "bot", text: res.answer },
      ]);
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 401) {
        logout(); // sesión expirada
        return;
      }
      setMessages((m) => [
        ...m,
        { id: Date.now() + "e", role: "bot", text: `⚠️ ${e.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
    >
      <FlatList
        data={messages}
        keyExtractor={(i) => i.id}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => (
          <View
            style={[
              styles.bubble,
              item.role === "user" ? styles.user : styles.bot,
            ]}
          >
            <Text
              style={item.role === "user" ? styles.userText : styles.botText}
            >
              {item.text}
            </Text>
          </View>
        )}
      />
      {loading && <ActivityIndicator style={{ marginBottom: 8 }} />}
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="Escribe tu consulta…"
          onSubmitEditing={onSend}
          returnKeyType="send"
        />
        <TouchableOpacity style={styles.sendBtn} onPress={onSend}>
          <Text style={styles.sendText}>Enviar</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  list: { padding: 12, gap: 8 },
  bubble: { maxWidth: "85%", padding: 12, borderRadius: 14 },
  user: { backgroundColor: "#2563eb", alignSelf: "flex-end" },
  bot: { backgroundColor: "#e2e8f0", alignSelf: "flex-start" },
  userText: { color: "#fff" },
  botText: { color: "#0f172a" },
  inputRow: { flexDirection: "row", padding: 10, gap: 8 },
  input: {
    flex: 1,
    backgroundColor: "#fff",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: "#cbd5e1",
  },
  sendBtn: {
    backgroundColor: "#2563eb",
    borderRadius: 12,
    paddingHorizontal: 18,
    justifyContent: "center",
  },
  sendText: { color: "#fff", fontWeight: "600" },
});
