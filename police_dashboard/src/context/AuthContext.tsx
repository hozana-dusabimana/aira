import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { auth } from '../services/api';
import type { User } from '../types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('aira_access_token');
    if (!token) {
      setLoading(false);
      return;
    }
    auth
      .me()
      .then(setUser)
      .catch(() => auth.logout())
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const tokens = await auth.login(email, password);
    auth.saveTokens(tokens);
    const me = await auth.me();
    setUser(me);
  }

  function logout() {
    auth.logout();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
