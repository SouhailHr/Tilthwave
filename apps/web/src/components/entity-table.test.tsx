import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EntityTable } from "./entity-table";

const useEntityList = vi.fn();
vi.mock("@/api/entity-queries", () => ({
  useEntityList: (...args: unknown[]) => useEntityList(...args),
  useDeleteEntity: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

type Row = { id: number; name: string };
const columns = [{ key: "name", header: "Name", cell: (row: Row) => row.name }];

function pageOf(page: number) {
  return {
    data: { items: [{ id: page, name: `row ${page}` }], total: 3, page, size: 1, pages: 3 },
    isPending: false,
    isError: false,
    error: null,
  };
}

afterEach(() => {
  vi.useRealTimers();
});

describe("EntityTable", () => {
  it("goes back to page 1 when the debounced search changes", async () => {
    // Regression: the comment promised this and nothing did it, so searching from page 3 showed
    // an empty page.
    vi.useFakeTimers();
    useEntityList.mockImplementation((_resource: string, params: { page: number }) => pageOf(params.page));
    render(<EntityTable<Row> resource="zones" title="Zones" columns={columns} pageSize={1} />);

    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(useEntityList).toHaveBeenLastCalledWith("zones", expect.objectContaining({ page: 2 }));

    fireEvent.change(screen.getByPlaceholderText(/search/i), { target: { value: "row" } });
    expect(useEntityList).toHaveBeenLastCalledWith("zones", expect.objectContaining({ page: 2 })); // not yet: debounced
    await act(async () => {
      vi.advanceTimersByTime(400);
    });
    expect(useEntityList).toHaveBeenLastCalledWith("zones", expect.objectContaining({ page: 1, search: "row" }));
  });
});
