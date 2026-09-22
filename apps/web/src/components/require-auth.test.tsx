import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RequireAuth } from "./require-auth";
import { emit } from "@/lib/eventBus";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ replace }),
}));

const useSession = vi.fn();
vi.mock("@/api/auth", () => ({
  sessionKey: ["auth", "me"],
  useSession: () => useSession(),
}));

const session = { user_id: 1, username: "admin", role: "admin", farm_name: "Sunny Farms", exp: 1 };

function renderGuarded() {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <RequireAuth>
        <div>secret dashboard</div>
      </RequireAuth>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  replace.mockClear();
  useSession.mockReset();
});

describe("RequireAuth", () => {
  it("renders children once the server confirms a session, without redirecting", async () => {
    useSession.mockReturnValue({ isPending: false, isSuccess: true, data: session });
    renderGuarded();
    await screen.findByText("secret dashboard");
    expect(replace).not.toHaveBeenCalled();
  });

  it("renders nothing and does not redirect while the probe is still pending", () => {
    // The old regression: a synchronous check redirected off an SSR placeholder before the real
    // value landed. Pending is now an explicit state, and pending never redirects.
    useSession.mockReturnValue({ isPending: true, isSuccess: false, data: undefined });
    renderGuarded();
    expect(screen.queryByText("secret dashboard")).toBeNull();
    expect(replace).not.toHaveBeenCalled();
  });

  it("redirects to /login when the server says nobody is signed in", async () => {
    useSession.mockReturnValue({ isPending: false, isSuccess: true, data: null });
    renderGuarded();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login?redirect=%2F"));
    expect(screen.queryByText("secret dashboard")).toBeNull();
  });

  it("does not treat a failed probe (API unreachable) as signed out", () => {
    useSession.mockReturnValue({ isPending: false, isSuccess: false, isError: true, data: undefined });
    renderGuarded();
    expect(screen.queryByText("secret dashboard")).toBeNull();
    expect(replace).not.toHaveBeenCalled();
  });

  it("drops the session and redirects with expired=1 on auth:expired", async () => {
    useSession.mockReturnValue({ isPending: false, isSuccess: true, data: session });
    renderGuarded();
    await screen.findByText("secret dashboard");
    emit({ type: "auth:expired", redirect: "/zones" });
    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/login?redirect=%2Fzones&expired=1"),
    );
  });
});
