"use client";

import { getApiErrorMessage } from "@/lib/api-error";
import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import api, { setAccessToken } from "@/lib/api";

const LOGOUT_FLAG_KEY = "forgeai_force_logged_out";

interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_two_factor_enabled: boolean;
  is_email_verified: boolean;
}

interface LoginResult {
  success: boolean;
  requiresTwoFactor: boolean;
  error?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (
    email: string,
    password: string,
    twoFactorCode?: string
  ) => Promise<LoginResult>;
  loginWithToken: (token: string) => Promise<boolean>;
  logout: () => Promise<void>;
  forceLocalLogout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function isForcedLoggedOut() {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(LOGOUT_FLAG_KEY) === "1";
}

function markForcedLoggedOut() {
  if (typeof window === "undefined") return;
  localStorage.setItem(LOGOUT_FLAG_KEY, "1");
}

function clearForcedLoggedOut() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(LOGOUT_FLAG_KEY);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const forceLocalLogout = useCallback(() => {
    setAccessToken(null);
    setUser(null);
  }, []);

  const fetchMe = useCallback(async () => {
    try {
      const res = await api.get<User>("/auth/me");
      setUser(res.data);
      return true;
    } catch {
      setUser(null);
      return false;
    }
  }, []);

  useEffect(() => {
    const bootstrapAuth = async () => {
      try {
        if (isForcedLoggedOut()) {
          forceLocalLogout();
          return;
        }

        const res = await api.post("/auth/refresh");
        setAccessToken(res.data.access_token);
        await fetchMe();
      } catch {
        setAccessToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    bootstrapAuth();
  }, [fetchMe, forceLocalLogout]);

  useEffect(() => {
    const handlePageShow = () => {
      if (isForcedLoggedOut()) {
        forceLocalLogout();
      }
    };

    const handleStorage = () => {
      if (isForcedLoggedOut()) {
        forceLocalLogout();
      }
    };

    window.addEventListener("pageshow", handlePageShow);
    window.addEventListener("storage", handleStorage);
    window.addEventListener("focus", handlePageShow);

    return () => {
      window.removeEventListener("pageshow", handlePageShow);
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener("focus", handlePageShow);
    };
  }, [forceLocalLogout]);

  const login = async (
    email: string,
    password: string,
    twoFactorCode?: string
  ): Promise<LoginResult> => {
    try {
      const res = await api.post("/auth/login", {
        email,
        password,
        two_factor_code: twoFactorCode,
      });

      if (res.data.requires_2fa) {
        return { success: false, requiresTwoFactor: true };
      }

      clearForcedLoggedOut();

      setAccessToken(res.data.access_token);
      await fetchMe();

      return { success: true, requiresTwoFactor: false };
    } catch (err: unknown) {
      return {
        success: false,
        requiresTwoFactor: false,
        error: getApiErrorMessage(err, "Erreur de connexion."),
      };
    }
  };

  const loginWithToken = useCallback(
    async (token: string): Promise<boolean> => {
      try {
        clearForcedLoggedOut();

        setAccessToken(token);

        const success = await fetchMe();

        if (!success) {
          setAccessToken(null);
          setUser(null);
          return false;
        }

        return true;
      } catch {
        setAccessToken(null);
        setUser(null);
        return false;
      }
    },
    [fetchMe]
  );

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // Même si le backend échoue, on nettoie côté frontend.
    } finally {
      markForcedLoggedOut();
      setAccessToken(null);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        login,
        loginWithToken,
        logout,
        forceLocalLogout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth doit être utilisé dans un AuthProvider");
  }

  return context;
}






