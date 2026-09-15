import { describe, expect, it, beforeEach } from "vitest";
import { getCurrentUserId, isAuthenticated } from "./auth";
import { setStoredToken, clearStoredToken } from "@/utils/tokenStorage";

function makeJwt(claims: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "none" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(claims)).toString("base64url");
  return `${header}.${body}.`;
}

beforeEach(() => {
  clearStoredToken();
});

describe("auth Flyweight + Zod claims", () => {
  it("returns null when no token stored", () => {
    expect(getCurrentUserId()).toBeNull();
    expect(isAuthenticated()).toBe(false);
  });

  it("returns user_id for a valid unexpired token", () => {
    const exp = Math.floor(Date.now() / 1000) + 3600;
    setStoredToken(makeJwt({ user_id: 42, exp }));
    expect(getCurrentUserId()).toBe(42);
    expect(isAuthenticated()).toBe(true);
  });

  it("treats missing exp as invalid (no NaN forever-token)", () => {
    setStoredToken(makeJwt({ user_id: 42 }));
    expect(getCurrentUserId()).toBeNull();
  });

  it("treats expired token as not authenticated", () => {
    const exp = Math.floor(Date.now() / 1000) - 1;
    setStoredToken(makeJwt({ user_id: 42, exp }));
    expect(getCurrentUserId()).toBeNull();
  });

  it("rejects malformed token payloads", () => {
    setStoredToken("not-a-jwt");
    expect(getCurrentUserId()).toBeNull();
  });
});