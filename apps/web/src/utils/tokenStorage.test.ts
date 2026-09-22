import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { setStoredToken, clearStoredToken } from "./tokenStorage";

/** A well-formed but unsigned-in-practice JWT: enough for jwt-decode, which never verifies. */
function fakeToken(payload: Record<string, unknown>) {
  const b64u = (o: object) => Buffer.from(JSON.stringify(o)).toString("base64url");
  return `${b64u({ alg: "HS256", typ: "JWT" })}.${b64u(payload)}.sig`;
}

function lastCookieWrite(spy: ReturnType<typeof vi.spyOn>): string {
  const calls = spy.mock.calls;
  return String(calls[calls.length - 1]?.[0]);
}

describe("tokenStorage cookie TTL", () => {
  let cookieSetSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // document.cookie can't be read back for Max-Age (browsers don't expose it), so the
    // assertion is on what gets *written* to it.
    cookieSetSpy = vi.spyOn(document, "cookie", "set").mockImplementation(() => {});
  });

  afterEach(() => {
    cookieSetSpy.mockRestore();
  });

  it("derives Max-Age from the token's own exp claim, not a fixed 24h", () => {
    // Regression for: the session cookie always lived for a flat 24h regardless of how long
    // the token itself was actually valid for, so the two could drift out of sync in either
    // direction.
    const oneHour = Math.floor(Date.now() / 1000) + 3600;
    setStoredToken(fakeToken({ user_id: 1, exp: oneHour }));

    const written = lastCookieWrite(cookieSetSpy);
    const match = written.match(/Max-Age=(\d+)/);
    expect(match).not.toBeNull();
    const maxAge = Number(match![1]);
    // Allow a few seconds of test-runtime drift instead of asserting an exact 3600.
    expect(maxAge).toBeGreaterThan(3590);
    expect(maxAge).toBeLessThanOrEqual(3600);
  });

  it("falls back to the old fixed 24h when the token has no exp claim", () => {
    setStoredToken(fakeToken({ user_id: 1 }));
    expect(lastCookieWrite(cookieSetSpy)).toContain("Max-Age=86400");
  });

  it("falls back to 24h for a token that can't be decoded at all", () => {
    setStoredToken("not-a-jwt");
    expect(lastCookieWrite(cookieSetSpy)).toContain("Max-Age=86400");
  });

  it("floors Max-Age at 0 for an already-expired token, rather than a negative value", () => {
    const past = Math.floor(Date.now() / 1000) - 3600;
    setStoredToken(fakeToken({ user_id: 1, exp: past }));
    expect(lastCookieWrite(cookieSetSpy)).toContain("Max-Age=0");
  });

  it("clears the cookie with Max-Age=0 on logout", () => {
    clearStoredToken();
    expect(lastCookieWrite(cookieSetSpy)).toContain("Max-Age=0");
  });
});
