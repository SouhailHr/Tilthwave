import { isAxiosError, type AxiosError } from "axios";

export interface ApiError {
  status: number;
  message: string;
  errorCode?: string;
  requestId?: string;
  cause?: unknown;
  fieldErrors?: Record<string, string[]>;
}

interface ApiErrorResponseBody {
  detail?: string | { msg?: string; loc?: (string | number)[] }[];
  error_code?: string;
  request_id?: string;
  message?: string;
  errors?: Record<string, string[]>;
}

export function toApiError(err: unknown, fallback = "Something went wrong"): ApiError {
  if (!isAxiosError(err)) {
    return { status: 0, message: err instanceof Error ? err.message : fallback };
  }
  const axErr = err as AxiosError<ApiErrorResponseBody>;
  const status = axErr.response?.status ?? 0;
  const body = axErr.response?.data;

  let message = fallback;
  let fieldErrors: Record<string, string[]> | undefined;

  if (body) {
    if (typeof body.detail === "string") {
      message = body.detail;
    } else if (Array.isArray(body.detail)) {
      // FastAPI validation errors
      fieldErrors = {};
      for (const item of body.detail) {
        const field = item.loc?.[item.loc.length - 1]?.toString() ?? "_";
        const msg = item.msg ?? fallback;
        (fieldErrors[field] ??= []).push(msg);
      }
      message = body.detail[0]?.msg ?? fallback;
    } else if (body.message) {
      message = body.message;
    }
  }

  return {
    status,
    message,
    errorCode: body?.error_code,
    requestId: body?.request_id,
    cause: err,
    fieldErrors,
  };
}

export function getErrorMessage(err: unknown, fallback: string): string {
  return toApiError(err, fallback).message;
}

export function toastDescription(apiError: { requestId?: string }): string | undefined {
  return apiError.requestId ? `ref: ${apiError.requestId}` : undefined;
}