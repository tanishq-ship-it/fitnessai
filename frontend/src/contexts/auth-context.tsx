import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { User } from "@/src/types/auth";
import * as authService from "@/src/services/auth-service";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  signUp: (email: string, password: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    (async () => {
      try {
        const token = await authService.getAccessToken();
        if (!token) {
          setIsLoading(false);
          return;
        }

        // Try to validate the stored token
        if (!authService.isTokenExpired(token)) {
          const me = await authService.getMe(token);
          setUser(me);
        } else {
          // Token expired — try refreshing
          const res = await authService.refreshTokens();
          setUser(res.user);
        }
      } catch {
        // Both token and refresh failed — user needs to log in
        await authService.clearTokens();
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    const res = await authService.signup(email, password);
    setUser(res.user);
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const res = await authService.login(email, password);
    setUser(res.user);
  }, []);

  const signOut = useCallback(async () => {
    const token = await authService.getAccessToken();
    if (token) {
      await authService.logout(token);
    } else {
      await authService.clearTokens();
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        signUp,
        signIn,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
