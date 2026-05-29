import { createContext, useContext, useMemo, useState } from "react";
import { loginAccount, registerAccount } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("datavault_token"));

  const value = useMemo(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      async login(payload) {
        const response = await loginAccount(payload);
        localStorage.setItem("datavault_token", response.access_token);
        setToken(response.access_token);
      },
      async register(payload) {
        const response = await registerAccount(payload);
        localStorage.setItem("datavault_token", response.access_token);
        setToken(response.access_token);
      },
      logout() {
        localStorage.removeItem("datavault_token");
        setToken(null);
      },
    }),
    [token]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
