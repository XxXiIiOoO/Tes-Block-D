import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { UNAUTHORIZED_EVENT } from "../api/client";
import {
  getMe,
  loginRequest,
  logoutRequest,
  registerRequest,
  verifyEmailRequest,
  updateMe,
  verifyTwoFactorRequest,
} from "../api/blocktest";
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "./storage";
import type { AuthResponse, LoginResponse, TwoFactorChallengeResponse, User } from "../types";
import { useAppPreferences } from "../preferences/AppPreferencesContext";


interface AuthContextValue {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (payload: { email: string; password: string }) => Promise<LoginResult>;
  verifyEmail: (payload: { token: string }) => Promise<void>;
  verifyTwoFactor: (payload: { email: string; code: string }) => Promise<void>;
  register: (payload: {
    email: string;
    username: string;
    password: string;
  }) => Promise<string>;
  updateProfile: (payload: {
    full_name?: string | null;
    position?: string | null;
    avatar_url?: string | null;
    bio?: string | null;
  }) => Promise<void>;
  logout: () => void;
}

type LoginResult =
  | { twoFactorRequired: false }
  | { twoFactorRequired: true; email: string; message: string };


const AuthContext = createContext<AuthContextValue | undefined>(undefined);


function applyAuthResponse(data: AuthResponse, setUser: (user: User | null) => void) {
  setTokens({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
  });
  setUser(data.user);
}

function isTwoFactorChallenge(data: LoginResponse): data is TwoFactorChallengeResponse {
  return "two_factor_required" in data && data.two_factor_required === true;
}


export function AuthProvider({ children }: { children: ReactNode }) {
  const { t } = useAppPreferences();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      const hasSession = Boolean(getAccessToken() || getRefreshToken());

      if (!hasSession) {
        if (active) {
          setLoading(false);
        }
        return;
      }

      try {
        const currentUser = await getMe();
        if (active) {
          setUser(currentUser);
        }
      } catch {
        clearTokens();
        if (active) {
          setUser(null);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    bootstrap();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    function handleUnauthorized() {
      clearTokens();
      setUser(null);
    }

    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => {
      window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    };
  }, []);

  async function login(payload: { email: string; password: string }): Promise<LoginResult> {
    const data = await loginRequest(payload);
    if (isTwoFactorChallenge(data)) {
      return {
        twoFactorRequired: true,
        email: data.email,
        message: data.message,
      };
    }
    applyAuthResponse(data, setUser);
    return { twoFactorRequired: false };
  }

  async function verifyTwoFactor(payload: { email: string; code: string }) {
    const data = await verifyTwoFactorRequest(payload);
    applyAuthResponse(data, setUser);
  }

  async function verifyEmail(payload: { token: string }) {
    const data = await verifyEmailRequest(payload);
    applyAuthResponse(data, setUser);
  }

  async function register(payload: {
    email: string;
    username: string;
    password: string;
  }) {
    await registerRequest(payload);
    return t("auth.register.success");
  }

  async function updateProfile(payload: {
    full_name?: string | null;
    position?: string | null;
    avatar_url?: string | null;
    bio?: string | null;
  }) {
    const updatedUser = await updateMe(payload);
    setUser(updatedUser);
  }

  function logout() {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      void logoutRequest({ refresh_token: refreshToken }).catch(() => undefined);
    }
    clearTokens();
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: Boolean(user),
        login,
        verifyEmail,
        verifyTwoFactor,
        register,
        updateProfile,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}


export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
