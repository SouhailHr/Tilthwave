import { beforeEach, describe, expect, it, vi } from "vitest";

const get = vi.fn();
const del = vi.fn();
vi.mock("@/api/client", () => ({ api: { get, delete: del } }));

beforeEach(() => {
  get.mockReset();
  del.mockReset();
});

describe("sessions", () => {
  it("lists the live sessions from the items envelope", async () => {
    const items = [{ id: 1, channel: "cookie", current: true }];
    get.mockResolvedValue({ data: { items } });
    const { fetchSessions } = await import("./account");
    expect(await fetchSessions()).toEqual(items);
    expect(get).toHaveBeenCalledWith("/account/sessions");
  });
});
