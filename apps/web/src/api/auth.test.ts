import { describe, expect, it, vi, beforeEach } from "vitest";

const get = vi.fn();
const post = vi.fn();
vi.mock("@/api/client", () => ({ api: { get, post } }));

const me = { user_id: 42, username: "admin", role: "admin", farm_name: "Sunny Farms", exp: 1 };
const unauthorized = { isAxiosError: true, response: { status: 401 } };

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("fetchSession", () => {
  it("returns the identity the API reports", async () => {
    get.mockResolvedValue({ data: me });
    const { fetchSession } = await import("./auth");
    expect(await fetchSession()).toEqual(me);
    expect(get).toHaveBeenCalledWith("/auth/me");
  });

  it("returns null on 401: nobody is signed in, not an error", async () => {
    get.mockRejectedValue(unauthorized);
    const { fetchSession } = await import("./auth");
    expect(await fetchSession()).toBeNull();
  });

  it("rethrows anything else (an outage is not 'signed out')", async () => {
    get.mockRejectedValue(new Error("network down"));
    const { fetchSession } = await import("./auth");
    await expect(fetchSession()).rejects.toThrow("network down");
  });

  it("rejects a malformed identity rather than trusting it", async () => {
    get.mockResolvedValue({ data: { username: "x" } });
    const { fetchSession } = await import("./auth");
    await expect(fetchSession()).rejects.toBeDefined();
  });
});

describe("login", () => {
  it("asks for a cookie session, stores nothing, and returns the identity", async () => {
    post.mockResolvedValue({ data: { token_type: "cookie" } });
    get.mockResolvedValue({ data: me });
    const { login } = await import("./auth");

    const session = await login({ username: "admin", password: "pw" });

    expect(post).toHaveBeenCalledTimes(1);
    const [url, body, config] = post.mock.calls[0];
    expect(url).toBe("/auth/login/");
    expect(body).toEqual({ username: "admin", password: "pw", use_cookie: true });
    expect(config?.headers?.["Idempotency-Key"]).toBeUndefined(); // never on a login
    expect(session).toEqual(me);
    expect(typeof window === "undefined" || window.localStorage.getItem("access")).toBeNull();
  });

  it("fails loudly if the cookie did not come back", async () => {
    post.mockResolvedValue({ data: { token_type: "cookie" } });
    get.mockRejectedValue(unauthorized);
    const { login } = await import("./auth");
    await expect(login({ username: "admin", password: "pw" })).rejects.toThrow(/cookie/);
  });
});

describe("logout", () => {
  it("posts to /auth/logout so the API clears the httpOnly cookie", async () => {
    post.mockResolvedValue({ status: 204 });
    const { logout } = await import("./auth");
    await logout();
    expect(post).toHaveBeenCalledWith("/auth/logout");
  });
});

describe("forgotten password", () => {
  it("forgotPassword posts the identifier and resolves on 202", async () => {
    post.mockResolvedValue({ status: 202, data: { detail: "If an account exists…" } });
    const { forgotPassword } = await import("./auth");
    await expect(forgotPassword("pat")).resolves.toBeUndefined();
    expect(post).toHaveBeenCalledWith("/auth/password/forgot", { identifier: "pat" });
  });

  it("resetPassword posts the token and the new password under the API's field name", async () => {
    post.mockResolvedValue({ status: 204 });
    const { resetPassword } = await import("./auth");
    await resetPassword("tok", "N3w-Passw0rd!");
    expect(post).toHaveBeenCalledWith("/auth/password/reset", {
      token: "tok",
      new_password: "N3w-Passw0rd!",
    });
  });

  it("resetPassword surfaces a rejected link so the page can say so", async () => {
    post.mockRejectedValue({ isAxiosError: true, response: { status: 400 } });
    const { resetPassword } = await import("./auth");
    await expect(resetPassword("bad", "N3w-Passw0rd!")).rejects.toBeDefined();
  });
});
