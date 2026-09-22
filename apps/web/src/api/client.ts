import axios, { AxiosError } from "axios";
import { emit } from "@/lib/eventBus";

// The session is an httpOnly cookie set by POST /auth/login (use_cookie: true): the browser
// attaches it on its own, and JavaScript - so any XSS payload - cannot read it. Because it is
// attached automatically, every state-changing request must also echo the readable CSRF cookie
// in a header; only same-origin JavaScript can read that cookie, so a cross-site page has the
// session but never the header. There is no token in localStorage any more, and nothing here
// ever sees one.
export const CSRF_COOKIE = "tw_csrf";
export const CSRF_HEADER = "X-CSRF-Token";
const SAFE_METHODS = new Set(["get", "head", "options"]);
// "Am I signed in?" A 401 from the probe is the normal answer for a visitor who never signed
// in, not an expired session, so it must not trigger the expired-session redirect.
const SESSION_PROBE = "/auth/me";

export function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

let isRedirecting = false;

api.interceptors.request.use((config) => {
  if (!SAFE_METHODS.has((config.method ?? "get").toLowerCase())) {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) config.headers[CSRF_HEADER] = csrf;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    const isProbe = (error.config?.url ?? "").endsWith(SESSION_PROBE);
    if (
      error.response?.status === 401 &&
      !isProbe &&
      typeof window !== "undefined" &&
      !isRedirecting
    ) {
      isRedirecting = true;
      const { pathname } = window.location;
      const redirect = pathname !== "/login" ? pathname : undefined;
      emit({ type: "auth:expired", redirect });
      // RequireAuth subscribes to the event, drops the cached session and uses next/navigation,
      // keeping the SPA tree alive. Reset the guard on the next tick so a real
      // session-expired-then-relogin cycle still works in the same tab.
      queueMicrotask(() => {
        isRedirecting = false;
      });
    }
    return Promise.reject(error);
  },
);
