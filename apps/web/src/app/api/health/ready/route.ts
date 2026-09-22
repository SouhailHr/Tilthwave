import { NextResponse } from "next/server";

/**
 * Real readiness: is the backend API actually reachable, the way the backend's own /health
 * checks its database. Separate from /api/health (which the container's own HEALTHCHECK uses
 * and must stay a pure liveness check - see that file). Meant for external monitoring, not for
 * anything that would restart this container on a downstream failure it can't fix.
 */
const API_TIMEOUT_MS = 2000;
// http://localhost:8080 so this still works for `next dev` on the host; the containerized web
// service overrides it via API_INTERNAL_URL to reach the API over the docker network instead of
// the host-facing NEXT_PUBLIC_API_BASE_URL.
const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8080";

async function checkApi(): Promise<"ok" | "unreachable"> {
  try {
    const res = await fetch(`${API_INTERNAL_URL}/health`, {
      signal: AbortSignal.timeout(API_TIMEOUT_MS),
    });
    return res.ok ? "ok" : "unreachable";
  } catch {
    return "unreachable";
  }
}

export async function GET() {
  const api = await checkApi();
  const body = { status: api === "ok" ? "ok" : "degraded", api, uptime: process.uptime() };
  return NextResponse.json(body, { status: api === "ok" ? 200 : 503 });
}
