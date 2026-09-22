import { NextResponse } from "next/server";

// Was `force-static`: a frozen build-time response can never say anything about the running
// process. This stays a pure liveness check (is the Next.js server itself answering) because
// the Dockerfile's own HEALTHCHECK pings this exact path and restarts the container on a
// non-2xx; failing it over an unrelated backend outage would restart a frontend that was never
// broken and can't fix the thing that actually failed. See /api/health/ready for a real
// downstream check.
export function GET() {
  return NextResponse.json({ status: "ok", uptime: process.uptime() });
}
