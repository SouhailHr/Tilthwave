import axios, { AxiosError } from "axios";
import { clearStoredToken, getStoredToken } from "@/utils/tokenStorage";
import { emit } from "@/lib/eventBus";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

let isRedirecting = false;

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if ((config.method ?? "").toLowerCase() === "post" && typeof crypto !== "undefined") {
    config.headers["Idempotency-Key"] = crypto.randomUUID();
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    if (
      error.response?.status === 401 &&
      typeof window !== "undefined" &&
      !isRedirecting
    ) {
      isRedirecting = true;
      const hadToken = getStoredToken() != null;
      clearStoredToken();
      const { pathname } = window.location;
      const redirect = pathname !== "/login" ? pathname : undefined;
      emit({ type: "auth:expired", redirect });
      // RequireAuth subscribes to the event and uses next/navigation, keeping
      // the SPA tree alive. Reset the guard on the next tick so a real
      // session-expired-then-relogin cycle still works in the same tab.
      queueMicrotask(() => {
        if (hadToken) isRedirecting = false;
      });
    }
    return Promise.reject(error);
  },
);