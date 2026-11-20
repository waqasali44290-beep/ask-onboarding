// Who is logged in, shared with every component through React context.
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, AUTH_EXPIRED_EVENT } from "./api/client";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  checking: boolean; // true until we know whether a session cookie is valid
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setChecking(false));

    // Any 401 from the API (session expired) sends the user back to the login page.
    const onExpired = () => setUser(null);
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    setUser(await api.login(username, password));
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
    }
  }, []);

  return <AuthContext.Provider value={{ user, checking, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const state = useContext(AuthContext);
  if (!state) throw new Error("useAuth must be used inside <AuthProvider>");
  return state;
}

/** The logged-in user; only call this inside pages that require a login. */
export function useUser(): User {
  const { user } = useAuth();
  if (!user) throw new Error("useUser called while logged out");
  return user;
}
