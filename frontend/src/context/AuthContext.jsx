import { createContext, useContext, useMemo, useState } from "react";
import api from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("stockflow_token"));
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("stockflow_user") || "null");
    } catch {
      return null;
    }
  });

  const saveAuth = (data) => {
    localStorage.setItem("stockflow_token", data.access_token);
    localStorage.setItem("stockflow_user", JSON.stringify(data.user));
    setToken(data.access_token);
    setUser(data.user);
  };
  const login = async (credentials) => saveAuth((await api.post("/auth/login", credentials)).data);
  const signup = async (credentials) => saveAuth((await api.post("/auth/signup", credentials)).data);
  const logout = () => {
    localStorage.removeItem("stockflow_token");
    localStorage.removeItem("stockflow_user");
    setToken(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({ token, user, isAuthenticated: Boolean(token), login, signup, logout }),
    [token, user],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider.");
  return value;
}
