import { jwtDecode } from "jwt-decode";
import { z } from "zod";

const ACCESS_KEY = "access";
const SESSION_COOKIE = "tw_logged_in";
const AUTH_CHANGE_EVENT = "tw-auth-change";
// Fallback only, for a token whose `exp` can't be read: keeps the previous fixed behavior
// rather than leaving the cookie unset.
const DEFAULT_COOKIE_MAX_AGE_SECONDS = 86400;

const storedShape = z.object({ token: z.string().min(1) });

let cachedToken: string | null | undefined; // undefined = not yet read

function readFromStorage(): string | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(ACCESS_KEY);
  if (!raw) return null;
  try {
    const parsed = storedShape.safeParse(JSON.parse(raw));
    return parsed.success ? parsed.data.token : null;
  } catch {
    return null;
  }
}

function notify() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

/**
 * Seconds until the token's own `exp` claim, so this UX-hint cookie (see middleware.ts) can't
 * outlive the token it's standing in for, or expire while the token is still good. Falls back
 * to the old fixed 24h for a token this can't read `exp` from, rather than leaving it unset.
 */
function cookieMaxAgeSeconds(token: string): number {
  try {
    const decoded = jwtDecode<{ exp?: unknown }>(token);
    if (typeof decoded.exp !== "number") return DEFAULT_COOKIE_MAX_AGE_SECONDS;
    return Math.max(0, Math.floor(decoded.exp - Date.now() / 1000));
  } catch {
    return DEFAULT_COOKIE_MAX_AGE_SECONDS;
  }
}

function setSessionCookie(maxAgeSeconds: number | null) {
  if (typeof document === "undefined") return;
  if (maxAgeSeconds !== null) {
    document.cookie = `${SESSION_COOKIE}=1; Path=/; SameSite=Lax; Max-Age=${maxAgeSeconds}`;
  } else {
    document.cookie = `${SESSION_COOKIE}=; Path=/; SameSite=Lax; Max-Age=0`;
  }
}

export function getStoredToken(): string | null {
  if (cachedToken === undefined) cachedToken = readFromStorage();
  return cachedToken;
}

export function setStoredToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_KEY, JSON.stringify({ token }));
  cachedToken = token;
  setSessionCookie(cookieMaxAgeSeconds(token));
  notify();
}

export function clearStoredToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_KEY);
  cachedToken = null;
  setSessionCookie(null);
  notify();
}

export function subscribeToTokenChanges(listener: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  const handleStorage = (e: StorageEvent) => {
    if (e.key !== ACCESS_KEY && e.key !== null) return;
    cachedToken = readFromStorage();
    listener();
  };
  const handleLocal = () => listener();
  window.addEventListener("storage", handleStorage);
  window.addEventListener(AUTH_CHANGE_EVENT, handleLocal);
  return () => {
    window.removeEventListener("storage", handleStorage);
    window.removeEventListener(AUTH_CHANGE_EVENT, handleLocal);
  };
}

export const SESSION_COOKIE_NAME = SESSION_COOKIE;