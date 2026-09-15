import { api } from "@/api/client";
import {
  useCreateEntity,
  useDeleteEntity,
  useEntity,
  useEntityList,
  useUpdateEntity,
} from "@/api/_entity";
import type {
  CreateWaterSourceInput,
  UpdateWaterSourceInput,
  WaterSource,
} from "@/types/water-source";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "water-sources";
const PATH = `/${RESOURCE}`;

export function fetchWaterSources(params: ListParams = {}) {
  return api
    .get<Paginated<WaterSource>>(`${PATH}/`, { params })
    .then((r) => r.data);
}

export function fetchWaterSource(id: number | string) {
  return api.get<WaterSource>(`${PATH}/${id}/`).then((r) => r.data);
}

export function createWaterSource(input: CreateWaterSourceInput) {
  return api.post<WaterSource>(`${PATH}/`, input).then((r) => r.data);
}

export function updateWaterSource(
  id: number | string,
  input: UpdateWaterSourceInput,
) {
  return api.patch<WaterSource>(`${PATH}/${id}/`, input).then((r) => r.data);
}

export function deleteWaterSource(id: number | string) {
  return api.delete(`${PATH}/${id}/`).then(() => id);
}

export const useWaterSources = (params: ListParams = {}) =>
  useEntityList<WaterSource>(RESOURCE, params);
export const useWaterSource = (id: number | string | null | undefined) =>
  useEntity<WaterSource>(RESOURCE, id);
export const useCreateWaterSource = () =>
  useCreateEntity<WaterSource, CreateWaterSourceInput>(RESOURCE);
export const useUpdateWaterSource = () =>
  useUpdateEntity<WaterSource, UpdateWaterSourceInput>(RESOURCE);
export const useDeleteWaterSource = () => useDeleteEntity(RESOURCE);