import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  entityChildKey,
  entityRootKey,
  useCreateEntity,
  useDeleteEntity,
  useEntity,
  useEntityList,
} from "@/api/_entity";
import { REFRESH_MS } from "@/api/constants";
import type { ApiError } from "@/api/errors";
import type {
  CreateFarmInput,
  Farm,
  FarmStats,
  UpdateFarmInput,
} from "@/types/farm";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "farms";
const PATH = `/${RESOURCE}`;

export function fetchFarms(params: ListParams = {}) {
  return api.get<Paginated<Farm>>(`${PATH}/`, { params }).then((r) => r.data);
}

export function fetchFarm(id: number | string) {
  return api.get<Farm>(`${PATH}/${id}/`).then((r) => r.data);
}

export function fetchFarmStats(farmName: string) {
  return api
    .get<FarmStats>(`${PATH}/stats/${encodeURIComponent(farmName)}/`)
    .then((r) => r.data);
}

export const useFarms = (params: ListParams = {}) =>
  useEntityList<Farm>(RESOURCE, params);
export const useFarm = (id: number | string | null | undefined) =>
  useEntity<Farm>(RESOURCE, id);
export const useCreateFarm = () =>
  useCreateEntity<Farm, CreateFarmInput>(RESOURCE);
export const useDeleteFarm = () => useDeleteEntity(RESOURCE);

export function useUpdateFarm() {
  const queryClient = useQueryClient();
  const mutation = useMutation<
    Farm,
    ApiError,
    { id: number | string; input: UpdateFarmInput }
  >({
    mutationFn: ({ id, input }) =>
      api.patch<Farm>(`${PATH}/${id}/`, input).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entityRootKey(RESOURCE) });
    },
  });
  return mutation;
}

export function useFarmStats(farmName: string | null | undefined) {
  return useQuery<FarmStats, ApiError>({
    queryKey: entityChildKey(RESOURCE, "stats", farmName ?? ""),
    enabled: !!farmName,
    queryFn: () => fetchFarmStats(farmName as string),
    refetchInterval: REFRESH_MS,
  });
}