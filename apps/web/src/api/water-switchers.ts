import { api } from "@/api/client";
import {
  useCreateEntity,
  useDeleteEntity,
  useEntity,
  useEntityList,
  useUpdateEntity,
} from "@/api/_entity";
import type {
  CreateWaterSwitcherInput,
  UpdateWaterSwitcherInput,
  WaterSwitcher,
} from "@/types/water-switcher";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "water-switchers";
const PATH = `/${RESOURCE}`;

export function fetchWaterSwitchers(params: ListParams = {}) {
  return api
    .get<Paginated<WaterSwitcher>>(`${PATH}/`, { params })
    .then((r) => r.data);
}

export function fetchWaterSwitcher(id: number | string) {
  return api.get<WaterSwitcher>(`${PATH}/${id}/`).then((r) => r.data);
}

export function createWaterSwitcher(input: CreateWaterSwitcherInput) {
  return api.post<WaterSwitcher>(`${PATH}/`, input).then((r) => r.data);
}

export function updateWaterSwitcher(
  id: number | string,
  input: UpdateWaterSwitcherInput,
) {
  return api.patch<WaterSwitcher>(`${PATH}/${id}/`, input).then((r) => r.data);
}

export function deleteWaterSwitcher(id: number | string) {
  return api.delete(`${PATH}/${id}/`).then(() => id);
}

export const useWaterSwitchers = (params: ListParams = {}) =>
  useEntityList<WaterSwitcher>(RESOURCE, params);
export const useWaterSwitcher = (id: number | string | null | undefined) =>
  useEntity<WaterSwitcher>(RESOURCE, id);
export const useCreateWaterSwitcher = () =>
  useCreateEntity<WaterSwitcher, CreateWaterSwitcherInput>(RESOURCE);
export const useUpdateWaterSwitcher = () =>
  useUpdateEntity<WaterSwitcher, UpdateWaterSwitcherInput>(RESOURCE);
export const useDeleteWaterSwitcher = () => useDeleteEntity(RESOURCE);