import { api } from "@/api/client";
import {
  useCreateEntity,
  useDeleteEntity,
  useEntity,
  useEntityList,
  useUpdateEntity,
} from "@/api/_entity";
import type {
  CreateIrrigationTaskInput,
  IrrigationTask,
  UpdateIrrigationTaskInput,
} from "@/types/irrigation-task";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "irrigation-tasks";
const PATH = `/${RESOURCE}`;

export function fetchIrrigationTasks(params: ListParams = {}) {
  return api
    .get<Paginated<IrrigationTask>>(`${PATH}/`, { params })
    .then((r) => r.data);
}

export function fetchIrrigationTask(id: number | string) {
  return api.get<IrrigationTask>(`${PATH}/${id}/`).then((r) => r.data);
}

export function createIrrigationTask(input: CreateIrrigationTaskInput) {
  return api.post<IrrigationTask>(`${PATH}/`, input).then((r) => r.data);
}

export function updateIrrigationTask(
  id: number | string,
  input: UpdateIrrigationTaskInput,
) {
  return api
    .patch<IrrigationTask>(`${PATH}/${id}/`, input)
    .then((r) => r.data);
}

export function deleteIrrigationTask(id: number | string) {
  return api.delete(`${PATH}/${id}/`).then(() => id);
}

export const useIrrigationTasks = (params: ListParams = {}) =>
  useEntityList<IrrigationTask>(RESOURCE, params);
export const useIrrigationTask = (id: number | string | null | undefined) =>
  useEntity<IrrigationTask>(RESOURCE, id);
export const useCreateIrrigationTask = () =>
  useCreateEntity<IrrigationTask, CreateIrrigationTaskInput>(RESOURCE);
export const useUpdateIrrigationTask = () =>
  useUpdateEntity<IrrigationTask, UpdateIrrigationTaskInput>(RESOURCE);
export const useDeleteIrrigationTask = () => useDeleteEntity(RESOURCE);