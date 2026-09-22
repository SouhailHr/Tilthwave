import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { RequireAuth } from "./require-auth";
import { setStoredToken, clearStoredToken } from "@/utils/tokenStorage";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ replace }),
}));

/** A well-formed but unsigned-in-practice JWT: enough for jwt-decode, which never verifies. */
function fakeToken(payload: Record<string, unknown>) {
  const b64u = (o: object) => Buffer.from(JSON.stringify(o)).toString("base64url");
  return `${b64u({ alg: "HS256", typ: "JWT" })}.${b64u(payload)}.sig`;
}

beforeEach(() => {
  replace.mockClear();
  clearStoredToken();
});

describe("RequireAuth", () => {
  it("renders children without redirecting when a valid token already exists (page refresh)", async () => {
    // Regression for: refreshing an authenticated page bounced to /login?redirect=%2F.
    // The token is set here, BEFORE the component mounts, exactly like a hard refresh where
    // the token was already in localStorage from a previous page load and no token-change
    // event fires during this component's lifecycle. useSyncExternalStore's server snapshot
    // is always "false", so without the `mounted` re-check this stayed stuck at "false" and
    // redirected every single time, even for an already-authenticated user.
    setStoredToken(fakeToken({ user_id: 1, exp: Math.floor(Date.now() / 1000) + 3600 }));

    render(
      <RequireAuth>
        <div>secret dashboard</div>
      </RequireAuth>,
    );

    await screen.findByText("secret dashboard");
    expect(replace).not.toHaveBeenCalled();
  });

  it("redirects to /login when no token exists", async () => {
    render(
      <RequireAuth>
        <div>secret dashboard</div>
      </RequireAuth>,
    );

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login?redirect=%2F"));
    expect(screen.queryByText("secret dashboard")).toBeNull();
  });

  it("redirects to /login when the stored token is expired", async () => {
    setStoredToken(fakeToken({ user_id: 1, exp: Math.floor(Date.now() / 1000) - 60 }));

    render(
      <RequireAuth>
        <div>secret dashboard</div>
      </RequireAuth>,
    );

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login?redirect=%2F"));
    expect(screen.queryByText("secret dashboard")).toBeNull();
  });
});
