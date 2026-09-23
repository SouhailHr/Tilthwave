import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import * as z from "zod";

import type { ApiError } from "@/api/errors";

import { EntityForm, type EntityFormField } from "./entity-form";

// The FK picker reads its options through the entity hooks; the text-furrow tests never reach it.
const useEntityList = vi.fn();
vi.mock("@/api/entity-queries", () => ({ useEntityList: (...args: unknown[]) => useEntityList(...args) }));

const schema = z.object({ zone_name: z.string().min(1, "Zone name is required") });
type Values = z.infer<typeof schema>;
const fields: EntityFormField<Values>[] = [{ name: "zone_name", label: "Zone name" }];

function renderForm(onSubmit: (values: Values) => Promise<void> | void) {
  return render(
    <EntityForm<Values> schema={schema} fields={fields} defaultValues={{ zone_name: "" }} onSubmit={onSubmit} />,
  );
}

describe("EntityForm", () => {
  it("does not submit an invalid form and shows the schema's message on the field", async () => {
    const onSubmit = vi.fn();
    renderForm(onSubmit);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Zone name is required")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits the parsed values", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderForm(onSubmit);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Zone A" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith({ zone_name: "Zone A" }));
  });

  it("puts the API's field errors on the fields they name", async () => {
    // A 422 used to be a toast saying "Field required" with no field; the CRUD page now rethrows
    // the ApiError and the form maps fieldErrors onto react-hook-form.
    const failure: ApiError = {
      status: 422,
      message: "Zone already exists",
      fieldErrors: { zone_name: ["A zone with this name already exists"], body: ["ignored: not a field"] },
    };
    const onSubmit = vi.fn().mockRejectedValue(failure);
    renderForm(onSubmit);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Zone A" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("A zone with this name already exists")).toBeInTheDocument();
    expect(screen.queryByText(/ignored/)).not.toBeInTheDocument();
  });
});

describe("FkSelect", () => {
  it("offers a server-side filter when the resource has more rows than a page", async () => {
    useEntityList.mockImplementation((_resource: string, params: { search?: string }) => ({
      data: {
        items: Array.from({ length: 100 }, (_, i) => ({ id: i, zone_name: `Zone ${i}` })).filter(
          (z) => !params.search || z.zone_name.includes(params.search),
        ),
        total: 340,
        page: 1,
        size: 100,
        pages: 4,
      },
      isPending: false,
      isError: false,
    }));
    const fkSchema = z.object({ zone_name: z.string() });
    render(
      <EntityForm<z.infer<typeof fkSchema>>
        schema={fkSchema}
        fields={[
          { name: "zone_name", label: "Zone", type: "fk", resource: "zones", valueKey: "zone_name", labelKey: "zone_name" },
        ]}
        defaultValues={{ zone_name: "" }}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByText(/Showing the first 100 of 340/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Filter zones"), { target: { value: "Zone 4" } });
    await waitFor(() =>
      expect(useEntityList).toHaveBeenLastCalledWith("zones", expect.objectContaining({ search: "Zone 4" })),
    );
  });
});
