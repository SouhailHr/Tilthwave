import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

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

describe("mutation hooks", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  function wrapperFor(client: QueryClient) {
    function Wrapper({ children }: { children: ReactNode }) {
      return createElement(QueryClientProvider, { client }, children);
    }
    return Wrapper;
  }

  it("useCreateEntity invalidates every query of the resource", async () => {
    vi.doMock("@/api/client", () => ({ api: { post: vi.fn().mockResolvedValue({ data: { id: 9 } }) } }));
    const { useCreateEntity } = await import("./entity-queries");
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useCreateEntity<{ id: number }, { zone_name: string }>("zones"), { wrapper: wrapperFor(client) });
    await result.current.mutateAsync({ zone_name: "Zone A" });
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ["zones"] }));
  });

  it("useUpdateEntity invalidates the resource and the row it changed", async () => {
    vi.doMock("@/api/client", () => ({ api: { patch: vi.fn().mockResolvedValue({ data: { id: 7 } }) } }));
    const { useUpdateEntity } = await import("./entity-queries");
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useUpdateEntity<{ id: number }, { size: number }>("zones"), { wrapper: wrapperFor(client) });
    await result.current.mutateAsync({ id: 7, input: { size: 2 } });
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ["zones", "detail", 7] }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["zones"] });
  });
});
