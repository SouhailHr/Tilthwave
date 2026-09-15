import { api } from "@/api/client";
import {
  useCreateEntity,
  useDeleteEntity,
  useEntity,
  useEntityList,
  useUpdateEntity,
} from "@/api/_entity";
import type {
  CreateZoneInput,
  UpdateZoneInput,
  Zone,
} from "@/types/zone";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "zones";
const PATH = `/${RESOURCE}`;

export function fetchZones(params: ListParams = {}) {
  return api.get<Paginated<Zone>>(`${PATH}/`, { params }).then((r) => r.data);
}

export function fetchZone(id: number | string) {
  return api.get<Zone>(`${PATH}/${id}/`).then((r) => r.data);
}

export function createZone(input: CreateZoneInput) {
  return api.post<Zone>(`${PATH}/`, input).then((r) => r.data);
}

export function updateZone(id: number | string, input: UpdateZoneInput) {
  return api.patch<Zone>(`${PATH}/${id}/`, input).then((r) => r.data);
}

export function deleteZone(id: number | string) {
  return api.delete(`${PATH}/${id}/`).then(() => id);
}

export const useZones = (params: ListParams = {}) =>
  useEntityList<Zone>(RESOURCE, params);
export const useZone = (id: number | string | null | undefined) =>
  useEntity<Zone>(RESOURCE, id);
export const useCreateZone = () =>
  useCreateEntity<Zone, CreateZoneInput>(RESOURCE);
export const useUpdateZone = () =>
  useUpdateEntity<Zone, UpdateZoneInput>(RESOURCE);
export const useDeleteZone = () => useDeleteEntity(RESOURCE);