import Constants from "expo-constants";

function getDevApiBaseUrl(): string {
  const explicitUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
  if (explicitUrl) {
    return explicitUrl;
  }

  const hostUri =
    Constants.expoConfig?.hostUri ?? Constants.platform?.hostUri ?? "";
  const host = hostUri.split(":")[0];

  if (host) {
    return `http://${host}:8000/api`;
  }

  return "http://localhost:8000/api";
}

export const API_BASE_URL = __DEV__
  ? getDevApiBaseUrl()
  : "https://your-production-url.com/api";

export const AUTH_ENDPOINTS = {
  SIGNUP: `${API_BASE_URL}/auth/signup`,
  LOGIN: `${API_BASE_URL}/auth/login`,
  REFRESH: `${API_BASE_URL}/auth/refresh`,
  LOGOUT: `${API_BASE_URL}/auth/logout`,
  ME: `${API_BASE_URL}/auth/me`,
} as const;
