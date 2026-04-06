// Use your computer's local IP so physical devices can reach the backend
export const API_BASE_URL = __DEV__
  ? "http://192.168.1.5:8000/api"
  : "https://your-production-url.com/api";
