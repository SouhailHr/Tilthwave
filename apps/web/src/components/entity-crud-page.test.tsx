import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as z from "zod";

import { EntityCrudPage } from "./entity-crud-page";

const rows = [{ id: 1, zone_name: "Zone A" }];
vi.mock("@/api/entity-queries", () => ({
  useEntityList: () => ({
    data: { items: rows, total: 1, page: 1, size: 20, pages: 1 },
    isPending: false,
    isError: false,
    error: null,
  }),
  useDeleteEntity: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
const toast = { success: vi.fn(), error: vi.fn() };
vi.mock("sonner", () => ({ toast: { success: (...a: unknown[]) => toast.success(...a), error: (...a: unknown[]) => toast.error(...a) } }));

type Row = (typeof rows)[number];
const schema = z.object({ zone_name: z.string().min(1, "Zone name is required") });
type Values = z.infer<typeof schema>;

const create = vi.fn();
const update = vi.fn();

function renderPage() {
  return render(
    <EntityCrudPage<Row, Values, Values, { zone_name: string }, { zone_name: string }>
      resource="zones"
      title="Zones"
      entity="zone"
      columns={[{ key: "zone_name", header: "Name", cell: (r) => r.zone_name }]}
      createSchema={schema}
      createFields={[{ name: "zone_name", label: "Zone name" }]}
      createDefaults={{ zone_name: "" }}
      toEditDefaults={(r) => ({ zone_name: r.zone_name })}
      toCreateInput={(v) => ({ zone_name: v.zone_name.trim() })}
      toUpdateInput={(v) => ({ zone_name: v.zone_name.trim() })}
      useCreate={() => ({ mutateAsync: create, isPending: false }) as never}
      useUpdate={() => ({ mutateAsync: update, isPending: false }) as never}
    />,
  );
}

beforeEach(() => {
  create.mockReset();
  update.mockReset();
  toast.success.mockClear();
  toast.error.mockClear();
});

describe("EntityCrudPage", () => {
  it("creates through the mapped input, toasts and closes the dialog", async () => {
    create.mockResolvedValue({ id: 2 });
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "New" }));
    expect(await screen.findByText("New zone")).toBeInTheDocument();
    fireEvent.change(within(screen.getByRole("dialog")).getByRole("textbox"), { target: { value: "  Zone B " } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith({ zone_name: "Zone B" }));
    expect(toast.success).toHaveBeenCalledWith("Zone created");
    await waitFor(() => expect(screen.queryByText("New zone")).toBeNull());
  });

  it("edits with the row's defaults and sends the id", async () => {
    update.mockResolvedValue({ id: 1 });
    renderPage();
    fireEvent.click(screen.getAllByRole("button", { name: "Row actions" })[0]);
    fireEvent.click(await screen.findByRole("menuitem", { name: /edit/i }));
    expect(await screen.findByText("Edit zone")).toBeInTheDocument();
    const input = within(screen.getByRole("dialog")).getByRole("textbox") as HTMLInputElement;
    expect(input.value).toBe("Zone A");
    fireEvent.change(input, { target: { value: "Zone A2" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(update).toHaveBeenCalledWith({ id: 1, input: { zone_name: "Zone A2" } }));
    expect(toast.success).toHaveBeenCalledWith("Zone updated");
  });

  it("toasts the API's message on failure and keeps the dialog open", async () => {
    create.mockRejectedValue({ status: 409, message: "Zone conflicts with an existing record" });
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "New" }));
    fireEvent.change(within(await screen.findByRole("dialog")).getByRole("textbox"), { target: { value: "Zone A" } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Zone conflicts with an existing record", expect.anything()));
    expect(screen.getByText("New zone")).toBeInTheDocument();
  });
});
