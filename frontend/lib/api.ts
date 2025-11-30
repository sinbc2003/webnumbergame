import axios from "axios";
import { getRuntimeConfig } from "./runtimeConfig";

const { apiBase } = getRuntimeConfig();

export const API_BASE = apiBase;

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

