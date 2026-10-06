import { createContext, useContext, useEffect, useState } from "react";
import { api, clearToken, getToken, setSession, setUnauthorizedHandler } from "./api";

const Context = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!getToken());

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    if (!getToken()) return;
    api("/auth/me")
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setReady(true));
  }, []);

  const start = (data) => {
    setSession(data);
    setUser(data.user);
  };

  const login = async (email, password) =>
    start(await api("/auth/login", { method: "POST", body: { email, password } }));

  const signup = async (fields) => start(await api("/auth/signup", { method: "POST", body: fields }));

  const changePassword = async (current_password, new_password) =>
    start(await api("/auth/change-password", { method: "POST", body: { current_password, new_password } }));

  const logout = () => {
    clearToken();
    setUser(null);
  };

  return (
    <Context.Provider value={{ user, ready, isAdmin: user?.role === "admin", login, signup, changePassword, logout }}>
      {children}
    </Context.Provider>
  );
}

export const useAuth = () => useContext(Context);
