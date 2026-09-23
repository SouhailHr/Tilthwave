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
  detail?: string;
  error_code?: string;
  request_id?: string;
  // Request-validation failures carry the messages per field (the API's one 422 shape).
  fields?: Record<string, string[]>;
  message?: string;
}

export function isApiError(err: unknown): err is ApiError {
  // An AxiosError also carries status + message; ApiError is a plain object, never an Error.
  return (
    typeof err === "object" &&
    err !== null &&
    !(err instanceof Error) &&
    typeof (err as ApiError).status === "number" &&
    typeof (err as ApiError).message === "string"
  );
}

/**
 * The one wire-to-domain boundary for failures. Idempotent: the entity fetchers already convert,
 * so a caller that converts again (the CRUD page, the table) gets the same error back, message
 * and field errors intact, instead of a fallback wrapped around a non-Error object.
 */
export function toApiError(err: unknown, fallback = "Something went wrong"): ApiError {
  if (isApiError(err)) return err;
  if (!isAxiosError(err)) {
    return { status: 0, message: err instanceof Error ? err.message : fallback };
  }
  const axErr = err as AxiosError<ApiErrorResponseBody>;
  const status = axErr.response?.status ?? 0;
  const body = axErr.response?.data;

  let message = fallback;
  let fieldErrors: Record<string, string[]> | undefined;

  if (body) {
    if (body.fields && Object.keys(body.fields).length > 0) {
      fieldErrors = body.fields;
    }
    if (typeof body.detail === "string") {
      message = body.detail;
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
