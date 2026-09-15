import type { ApiError } from "@/api/errors";

export type AppEvent =
  | { type: "auth:expired"; redirect?: string }
  | { type: "api:error"; error: ApiError; source: "query" | "mutation" | "interceptor" };

type Listener = (event: AppEvent) => void;

const listeners = new Set<Listener>();

export function emit(event: AppEvent) {
  for (const listener of listeners) {
    try {
      listener(event);
    } catch {
      // listener failures must not break the bus
    }
  }
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}