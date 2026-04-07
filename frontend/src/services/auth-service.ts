import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";
import { AUTH_ENDPOINTS } from "@/src/constants/api";
import { AuthResponse, User } from "@/src/types/auth";

const ACCESS_TOKEN_KEY = "fitnessai_access_token";
const REFRESH_TOKEN_KEY = "fitnessai_refresh_token";

// ── Token Storage ──
// SecureStore works on iOS/Android. Falls back to nothing on web.

async function setItem(key: string, value: string): Promise<void> {
  if (Platform.OS === "web") {
    localStorage.setItem(key, value);
  } else {
    await SecureStore.setItemAsync(key, value);
  }
}

async function getItem(key: string): Promise<string | null> {
  if (Platform.OS === "web") {
    return localStorage.getItem(key);
  }
  return SecureStore.getItemAsync(key);
}

async function deleteItem(key: string): Promise<void> {
  if (Platform.OS === "web") {
    localStorage.removeItem(key);
  } else {
    await SecureStore.deleteItemAsync(key);
  }
}

export async function storeTokens(
  accessToken: string,
  refreshToken: string
): Promise<void> {
  await setItem(ACCESS_TOKEN_KEY, accessToken);
  await setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export async function getAccessToken(): Promise<string | null> {
  return getItem(ACCESS_TOKEN_KEY);
}

export async function getRefreshToken(): Promise<string | null> {
  return getItem(REFRESH_TOKEN_KEY);
}

export async function clearTokens(): Promise<void> {
  await deleteItem(ACCESS_TOKEN_KEY);
  await deleteItem(REFRESH_TOKEN_KEY);
}

// ── JWT Expiry Check (client-side, no crypto verification) ──

export function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    // Expired if within 60 seconds of expiry
    return payload.exp * 1000 < Date.now() + 60_000;
  } catch {
    return true;
  }
}

// ── API Calls ──

async function apiCall<T>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export async function signup(
  email: string,
  password: string
): Promise<AuthResponse> {
  const data = await apiCall<AuthResponse>(AUTH_ENDPOINTS.SIGNUP, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  await storeTokens(data.access_token, data.refresh_token);
  return data;
}

export async function login(
  email: string,
  password: string
): Promise<AuthResponse> {
  const data = await apiCall<AuthResponse>(AUTH_ENDPOINTS.LOGIN, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  await storeTokens(data.access_token, data.refresh_token);
  return data;
}

export async function refreshTokens(): Promise<AuthResponse> {
  const refreshToken = await getRefreshToken();
  if (!refreshToken) throw new Error("No refresh token");

  const data = await apiCall<AuthResponse>(AUTH_ENDPOINTS.REFRESH, {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  await storeTokens(data.access_token, data.refresh_token);
  return data;
}

export async function logout(accessToken: string): Promise<void> {
  const refreshToken = await getRefreshToken();
  if (refreshToken) {
    try {
      await apiCall(AUTH_ENDPOINTS.LOGOUT, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch {
      // Best-effort logout — clear tokens regardless
    }
  }
  await clearTokens();
}

export async function getMe(accessToken: string): Promise<User> {
  return apiCall<User>(AUTH_ENDPOINTS.ME, {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

// ── Get Valid Access Token (with auto-refresh) ──

let refreshPromise: Promise<string> | null = null;

export async function getValidAccessToken(): Promise<string> {
  const token = await getAccessToken();
  if (token && !isTokenExpired(token)) return token;

  // Deduplicate concurrent refresh calls
  if (!refreshPromise) {
    refreshPromise = refreshTokens()
      .then((res) => {
        refreshPromise = null;
        return res.access_token;
      })
      .catch((err) => {
        refreshPromise = null;
        throw err;
      });
  }
  return refreshPromise;
}
