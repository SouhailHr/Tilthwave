import { api } from "@/api/client";
import {
  useCreateEntity,
  useDeleteEntity,
  useEntity,
  useEntityList,
  useUpdateEntity,
} from "@/api/_entity";
import type {
  CreateSensorInput,
  Sensor,
  UpdateSensorInput,
} from "@/types/sensor";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "sensors";
const PATH = `/${RESOURCE}`;

export function fetchSensors(params: ListParams = {}) {
  return api.get<Paginated<Sensor>>(`${PATH}/`, { params }).then((r) => r.data);
}

export function fetchSensor(id: number | string) {
  return api.get<Sensor>(`${PATH}/${id}/`).then((r) => r.data);
}

export function createSensor(input: CreateSensorInput) {
  return api.post<Sensor>(`${PATH}/`, input).then((r) => r.data);
}

export function updateSensor(id: number | string, input: UpdateSensorInput) {
  return api.patch<Sensor>(`${PATH}/${id}/`, input).then((r) => r.data);
}

export function deleteSensor(id: number | string) {
  return api.delete(`${PATH}/${id}/`).then(() => id);
}

export const useSensors = (params: ListParams = {}) =>
  useEntityList<Sensor>(RESOURCE, params);
export const useSensor = (id: number | string | null | undefined) =>
  useEntity<Sensor>(RESOURCE, id);
export const useCreateSensor = () =>
  useCreateEntity<Sensor, CreateSensorInput>(RESOURCE);
export const useUpdateSensor = () =>
  useUpdateEntity<Sensor, UpdateSensorInput>(RESOURCE);
export const useDeleteSensor = () => useDeleteEntity(RESOURCE);