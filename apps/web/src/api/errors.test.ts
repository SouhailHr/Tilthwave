import { AxiosError, type AxiosResponse } from "axios";
import { describe, expect, it } from "vitest";

import { toApiError } from "./errors";

function fakeAxiosError(
  status: number,
  data: unknown,
): AxiosError {
  const err = new AxiosError("Request failed");
  err.response = { status, data, headers: {}, config: {}, statusText: "" } as AxiosResponse;
  err.isAxiosError = true;
  return err;
}

describe("toApiError", () => {
  it("returns fallback for non-axios errors", () => {
    expect(toApiError(new Error("boom"), "fallback")).toEqual({
      status: 0,
      message: "boom",
    });
    expect(toApiError("string error", "fallback")).toEqual({
      status: 0,
      message: "fallback",
    });
  });

  it("extracts string detail from FastAPI envelope", () => {
    const err = fakeAxiosError(400, { detail: "bad input" });
    expect(toApiError(err, "fallback").message).toBe("bad input");
  });

  it("surfaces errorCode and requestId when present", () => {
    const err = fakeAxiosError(500, {
      detail: "internal",
      error_code: "E_INTERNAL",
      request_id: "req-123",
    });
    const result = toApiError(err);
    expect(result.errorCode).toBe("E_INTERNAL");
    expect(result.requestId).toBe("req-123");
  });

  it("falls back to provided message when body is empty", () => {
    const err = fakeAxiosError(500, {});
    expect(toApiError(err, "fallback").message).toBe("fallback");
  });
});

describe("toApiError with the API's validation envelope", () => {
  it("takes the fields map and the summary detail", () => {
    const err = new AxiosError("Request failed with status code 422", "ERR_BAD_REQUEST", undefined, undefined, {
      status: 422,
      statusText: "",
      headers: {},
      config: {} as never,
      data: {
        detail: "size: Input should be a valid number",
        error_code: "validation_error",
        request_id: "abc123",
        fields: { size: ["Input should be a valid number"], soil_type: ["Input should be a valid string"] },
      },
    });
    const apiError = toApiError(err);
    expect(apiError.status).toBe(422);
    expect(apiError.message).toBe("size: Input should be a valid number");
    expect(apiError.errorCode).toBe("validation_error");
    expect(apiError.requestId).toBe("abc123");
    expect(apiError.fieldErrors).toEqual({
      size: ["Input should be a valid number"],
      soil_type: ["Input should be a valid string"],
    });
  });
});
