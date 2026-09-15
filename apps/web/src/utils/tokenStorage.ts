import { z } from "zod";

const ACCESS_KEY = "access";
const SESSION_COOKIE = "tw_logged_in";
const AUTH_CHANGE_EVENT = "tw-auth-change";

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

function setSessionCookie(present: boolean) {
  if (typeof document === "undefined") return;
  if (present) {
    document.cookie = `${SESSION_COOKIE}=1; Path=/; SameSite=Lax; Max-Age=86400`;
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
  setSessionCookie(true);
  notify();
}

export function clearStoredToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_KEY);
  cachedToken = null;
  setSessionCookie(false);
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