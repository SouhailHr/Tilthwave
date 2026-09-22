import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/api/client";
import { toApiError, type ApiError } from "@/api/errors";
import type { EntityWithId, ListParams, Paginated } from "@/types/pagination";

// URL shapes mirror the API's routes exactly: collections end with a slash (`/zones/`), items do
// not (`/zones/1`). The API does not redirect a mismatch (redirect_slashes is off), so a wrong
// shape is a loud 404 here rather than a silent extra round trip.
//
// Every fetcher rejects with an ApiError, so the `ApiError` type parameter on the hooks below is
// true and error UIs show the API's message, not axios's "Request failed with status code 500".
const rejectAsApiError = (err: unknown): never => {
  throw toApiError(err);
};

export function fetchEntityList<T>(resource: string, params: ListParams = {}) {
  return api
    .get<Paginated<T>>(`/${resource}/`, { params })
    .then((res) => res.data, rejectAsApiError);
}

export function fetchEntity<T>(resource: string, id: number | string) {
  return api.get<T>(`/${resource}/${id}`).then((res) => res.data, rejectAsApiError);
}

export function createEntity<T, TInput = Partial<T>>(
  resource: string,
  input: TInput,
) {
  return api.post<T>(`/${resource}/`, input).then((res) => res.data, rejectAsApiError);
}

export function updateEntity<T, TInput = Partial<T>>(
  resource: string,
  id: number | string,
  input: TInput,
) {
  return api.patch<T>(`/${resource}/${id}`, input).then((res) => res.data, rejectAsApiError);
}

export function deleteEntity(resource: string, id: number | string) {
  return api.delete(`/${resource}/${id}`).then(() => id, rejectAsApiError);
}

export function entityListKey(resource: string, params: ListParams) {
  return [resource, "list", params] as const;
}

export function entityDetailKey(resource: string, id: number | string) {
  return [resource, "detail", id] as const;
}

export function entityRootKey(resource: string) {
  return [resource] as const;
}

export function entityChildKey(
  resource: string,
  child: string,
  ...rest: (string | number)[]
) {
  return [resource, child, ...rest] as const;
}

export function useEntityList<T>(resource: string, params: ListParams = {}) {
  return useQuery<Paginated<T>, ApiError>({
    queryKey: entityListKey(resource, params),
    queryFn: () => fetchEntityList<T>(resource, params),
    placeholderData: keepPreviousData,
  });
}

export function useEntity<T>(
  resource: string,
  id: number | string | null | undefined,
) {
  return useQuery<T, ApiError>({
    queryKey: entityDetailKey(resource, id ?? ""),
    enabled: id != null,
    queryFn: () => fetchEntity<T>(resource, id as number | string),
  });
}

export function useCreateEntity<T extends EntityWithId, TInput = Partial<T>>(
  resource: string,
) {
  const queryClient = useQueryClient();
  return useMutation<T, ApiError, TInput>({
    mutationFn: (input) => createEntity<T, TInput>(resource, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entityRootKey(resource) });
    },
  });
}

export function useUpdateEntity<T extends EntityWithId, TInput = Partial<T>>(
  resource: string,
) {
  const queryClient = useQueryClient();
  return useMutation<T, ApiError, { id: number | string; input: TInput }>({
    mutationFn: ({ id, input }) => updateEntity<T, TInput>(resource, id, input),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: entityRootKey(resource) });
      queryClient.invalidateQueries({ queryKey: entityDetailKey(resource, id) });
    },
  });
}

export function useDeleteEntity(resource: string) {
  const queryClient = useQueryClient();
  return useMutation<number | string, ApiError, number | string>({
    mutationFn: (id) => deleteEntity(resource, id),
    onSuccess: (id) => {
      queryClient.invalidateQueries({ queryKey: entityRootKey(resource) });
      queryClient.invalidateQueries({ queryKey: entityDetailKey(resource, id) });
    },
  });
}