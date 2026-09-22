"use client";

import { useEffect } from "react";
import type { ReactNode } from "react";
import { toast } from "sonner";
import { subscribe } from "@/lib/eventBus";

/**
 * The one consumer of the `api:error` event QueryProvider emits on every query and mutation
 * failure. Before this, the event bus had zero subscribers for it (only `auth:expired` was
 * ever handled, by RequireAuth), so every non-401 failure - a flaky dashboard poll, a create
 * that 500s - vanished with nothing to show for it and nothing to debug from afterward.
 *
 * Mutation failures already surface a toast at the call site (entity-crud-page.tsx,
 * entity-table.tsx) via toApiError, so toasting them again here would double up. Query
 * failures (the dashboard's live-polling cards, any future bare `useQuery`) have no error UI
 * anywhere else, so those get one. Every failure is logged regardless, since nothing logged
 * them before; this is a starting point for a real telemetry vendor, not a replacement for one
 * (see docs/BACKLOG.md, "Telemetry").
 */
export function ObservabilitySink({ children }: { children: ReactNode }) {
  useEffect(() => {
    return subscribe((event) => {
      if (event.type !== "api:error") return;
      const { error, source } = event;
      console.error(`[api:error:${source}]`, error);
      if (source !== "query") return;
      toast.error(error.message, {
        description: error.requestId ? `Ref: ${error.requestId}` : undefined,
      });
    });
  }, []);

  return <>{children}</>;
}
