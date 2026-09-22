import { describe, expect, it, vi, beforeEach } from "vitest";

import {
  entityChildKey,
  entityDetailKey,
  entityListKey,
  entityRootKey,
} from "./_entity";

describe("Generic Repository key helpers", () => {
  it("entityListKey is parameterised by params", () => {
    expect(entityListKey("zones", { page: 1, size: 20 })).toEqual([
      "zones",
      "list",
      { page: 1, size: 20 },
    ]);
  });

  it("entityDetailKey nests the id under the resource", () => {
    expect(entityDetailKey("farms", 7)).toEqual(["farms", "detail", 7]);
  });

  it("entityRootKey is the invalidation prefix that matches list + detail", () => {
    const root = entityRootKey("sensors");
    expect(root).toEqual(["sensors"]);
    expect(entityListKey("sensors", {}).slice(0, 1)).toEqual(root);
    expect(entityDetailKey("sensors", 1).slice(0, 1)).toEqual(root);
  });

  it("entityChildKey supports stats / sub-resources", () => {
    expect(entityChildKey("farms", "stats", "Sunny")).toEqual([
      "farms",
      "stats",
      "Sunny",
    ]);
    expect(entityChildKey("farms", "stats", "Sunny").slice(0, 1)).toEqual(
      entityRootKey("farms"),
    );
  });
});

type Handlers = {
  handlers: { fulfilled: (cfg: unknown) => unknown; rejected: (err: unknown) => unknown }[];
};

describe("client interceptors", () => {
  beforeEach(() => {
    vi.resetModules();
    document.cookie = "tw_csrf=; Max-Age=0; Path=/";
  });

  it("emits auth:expired on a 401 (and nothing else clears: the cookie is the server's)", async () => {
    const events: { type: string }[] = [];
    vi.doMock("@/lib/eventBus", () => ({
      emit: (e: { type: string }) => events.push(e),
      subscribe: () => () => {},
    }));

    const { api } = await import("./client");
    const rejected = (api.interceptors.response as unknown as Handlers).handlers[0]?.rejected;
    expect(rejected).toBeTypeOf("function");

    await expect(
      rejected({ response: { status: 401 }, config: { url: "/zones/" }, isAxiosError: true }),
    ).rejects.toBeDefined();
    expect(events.some((e) => e.type === "auth:expired")).toBe(true);
  });

  it("does not emit auth:expired for a 401 from the /auth/me probe (nobody signed in is not an expiry)", async () => {
    const events: { type: string }[] = [];
    vi.doMock("@/lib/eventBus", () => ({
      emit: (e: { type: string }) => events.push(e),
      subscribe: () => () => {},
    }));

    const { api } = await import("./client");
    const rejected = (api.interceptors.response as unknown as Handlers).handlers[0]?.rejected;

    await expect(
      rejected({ response: { status: 401 }, config: { url: "/auth/me" }, isAxiosError: true }),
    ).rejects.toBeDefined();
    expect(events).toEqual([]);
  });

  it("sends the CSRF cookie back as a header on mutations only, and sends credentials", async () => {
    document.cookie = "tw_csrf=abc123; Path=/";
    const { api, CSRF_HEADER } = await import("./client");
    expect(api.defaults.withCredentials).toBe(true);
    const fulfilled = (api.interceptors.request as unknown as Handlers).handlers[0]?.fulfilled;

    const post = fulfilled({ method: "post", headers: {} }) as { headers: Record<string, string> };
    expect(post.headers[CSRF_HEADER]).toBe("abc123");
    const del = fulfilled({ method: "delete", headers: {} }) as { headers: Record<string, string> };
    expect(del.headers[CSRF_HEADER]).toBe("abc123");
    const get = fulfilled({ method: "get", headers: {} }) as { headers: Record<string, string> };
    expect(get.headers[CSRF_HEADER]).toBeUndefined();
  });
});

describe("createEntity Idempotency-Key", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("attaches a fresh key per call, scoped to this request only", async () => {
    // Regression for: the key used to be generated in the axios request interceptor, so it
    // fired for every POST including /auth/login (which must never carry one), and a key
    // generated there can't survive being the same across a retry of one logical attempt.
    const post = vi.fn().mockResolvedValue({ data: { id: 1 } });
    vi.doMock("@/api/client", () => ({ api: { post } }));

    const { createEntity } = await import("./_entity");
    await createEntity("zones", { zone_name: "Zone A" });
    await createEntity("zones", { zone_name: "Zone B" });

    expect(post).toHaveBeenCalledTimes(2);
    const [, , firstConfig] = post.mock.calls[0];
    const [, , secondConfig] = post.mock.calls[1];
    const firstKey = firstConfig.headers["Idempotency-Key"];
    const secondKey = secondConfig.headers["Idempotency-Key"];
    expect(firstKey).toEqual(expect.any(String));
    expect(firstKey).not.toBe(secondKey);
  });
});
