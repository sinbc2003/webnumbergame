import axios from "axios";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

let authToken: string | null = null;

export const setAuthToken = (token: string | null) => {
  authToken = token;
};

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: false,
  timeout: 10000
});

api.interceptors.request.use((config) => {
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

export default api;

