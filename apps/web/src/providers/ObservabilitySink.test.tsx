import { render } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import type { ApiError } from "@/api/errors";
import { emit } from "@/lib/eventBus";

import { ObservabilitySink } from "./ObservabilitySink";


const toastError = vi.fn();
vi.mock("sonner", () => ({
  toast: { error: (...args: unknown[]) => toastError(...args) },
}));

const error: ApiError = { status: 500, message: "boom", requestId: "req-1" };

beforeEach(() => {
  toastError.mockClear();
  vi.spyOn(console, "error").mockImplementation(() => {});
});

describe("ObservabilitySink", () => {
  it("toasts a query-source api:error (no other UI shows these)", () => {
    render(
      <ObservabilitySink>
        <div />
      </ObservabilitySink>,
    );
    emit({ type: "api:error", error, source: "query" });
    expect(toastError).toHaveBeenCalledWith("boom", { description: "Ref: req-1" });
  });

  it("does not toast a mutation-source api:error (entity-crud-page/entity-table already do)", () => {
    render(
      <ObservabilitySink>
        <div />
      </ObservabilitySink>,
    );
    emit({ type: "api:error", error, source: "mutation" });
    expect(toastError).not.toHaveBeenCalled();
  });

  it("logs every source, including ones it does not toast", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ObservabilitySink>
        <div />
      </ObservabilitySink>,
    );
    emit({ type: "api:error", error, source: "interceptor" });
    expect(spy).toHaveBeenCalledWith("[api:error:interceptor]", error);
    expect(toastError).not.toHaveBeenCalled();
  });

  it("ignores unrelated events", () => {
    render(
      <ObservabilitySink>
        <div />
      </ObservabilitySink>,
    );
    emit({ type: "auth:expired" });
    expect(toastError).not.toHaveBeenCalled();
  });
});
