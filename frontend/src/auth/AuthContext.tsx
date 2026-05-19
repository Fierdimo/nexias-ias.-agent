/** Sesión disponible para cualquier pantalla sin prop-drilling. */
import { createContext, useContext, type ReactNode } from "react";

import type { Profile } from "../api/client";

type AuthValue = {
  token: string;
  profile: Profile;
  logout: () => void;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({
  value,
  children,
}: {
  value: AuthValue;
  children: ReactNode;
}) {
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
