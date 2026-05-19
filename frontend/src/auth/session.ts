/**
 * Persistencia de sesión en el dispositivo con expo-secure-store
 * (almacenamiento cifrado: Keychain en iOS, Keystore en Android).
 */
import * as SecureStore from "expo-secure-store";

import type { Profile } from "../api/client";

const TOKEN_KEY = "nexias.access_token";
const PROFILE_KEY = "nexias.profile";

export type Session = { token: string; profile: Profile };

export async function saveSession(s: Session): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, s.token);
  await SecureStore.setItemAsync(PROFILE_KEY, JSON.stringify(s.profile));
}

export async function loadSession(): Promise<Session | null> {
  const token = await SecureStore.getItemAsync(TOKEN_KEY);
  const profileRaw = await SecureStore.getItemAsync(PROFILE_KEY);
  if (!token || !profileRaw) return null;
  try {
    return { token, profile: JSON.parse(profileRaw) as Profile };
  } catch {
    return null;
  }
}

export async function clearSession(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(PROFILE_KEY);
}
