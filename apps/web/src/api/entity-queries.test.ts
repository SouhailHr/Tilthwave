import { describe, expect, it, vi, beforeEach } from "vitest";

import {
  entityChildKey,
  entityDetailKey,
  entityListKey,
  entityRootKey,
} from "./entity-queries";

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

describe("entity fetchers", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("addresses collections with a trailing slash and items without one", async () => {
    // The API does not redirect a mismatched slash (redirect_slashes is off): the old `/zones/7/`
    // shape cost a 307 per call and, behind a proxy, could bounce the browser to http://.
    const get = vi.fn().mockResolvedValue({ data: {} });
    const post = vi.fn().mockResolvedValue({ data: {} });
    const patch = vi.fn().mockResolvedValue({ data: {} });
    const del = vi.fn().mockResolvedValue({});
    vi.doMock("@/api/client", () => ({ api: { get, post, patch, delete: del } }));

    const { fetchEntityList, fetchEntity, createEntity, updateEntity, deleteEntity } = await import("./entity-queries");
    await fetchEntityList("zones", { page: 1 });
    await fetchEntity("zones", 7);
    await createEntity("zones", { zone_name: "Zone A" });
    await updateEntity("zones", 7, { size: 1 });
    await deleteEntity("zones", 7);

    expect(get.mock.calls.map((c) => c[0])).toEqual(["/zones/", "/zones/7"]);
    expect(post.mock.calls[0][0]).toBe("/zones/");
    expect(patch.mock.calls[0][0]).toBe("/zones/7");
    expect(del.mock.calls[0][0]).toBe("/zones/7");
    // No per-request headers any more: the Idempotency-Key the backend never read is gone.
    expect(post.mock.calls[0][2]).toBeUndefined();
  });

  it("rejects with an ApiError carrying the API's message, not axios's", async () => {
    const { AxiosError } = await import("axios");
    const failure = new AxiosError(
      "Request failed with status code 500",
      "ERR_BAD_RESPONSE",
      undefined,
      undefined,
      { status: 500, statusText: "", headers: {}, config: {} as never, data: { detail: "Database error" } },
    );
    const get = vi.fn().mockRejectedValue(failure);
    vi.doMock("@/api/client", () => ({ api: { get } }));

    const { fetchEntity } = await import("./entity-queries");
    await expect(fetchEntity("zones", 1)).rejects.toMatchObject({ status: 500, message: "Database error" });
  });
});
