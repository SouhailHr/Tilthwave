import { api } from "@/api/client";
import { useCreateEntity, useUpdateEntity } from "@/api/_entity";
import type {
  CreateIrrigationTaskInput,
  IrrigationTask,
  UpdateIrrigationTaskInput,
} from "@/types/irrigation-task";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "irrigation-tasks";
const PATH = `/${RESOURCE}`;

// The dashboard polls this directly (bypasses the generic EntityTable/EntityCrudPage path, so
// it isn't covered by _entity.ts's fetchEntityList call site). Everything else this module used
// to duplicate - fetchIrrigationTask, createIrrigationTask, updateIrrigationTask,
// deleteIrrigationTask, useIrrigationTasks, useIrrigationTask, useDeleteIrrigationTask - had
// zero callers: EntityTable/EntityCrudPage already get list and delete generically from
// _entity.ts given just the resource string.
export function fetchIrrigationTasks(params: ListParams = {}) {
  return api
    .get<Paginated<IrrigationTask>>(`${PATH}/`, { params })
    .then((r) => r.data);
}

export const useCreateIrrigationTask = () =>
  useCreateEntity<IrrigationTask, CreateIrrigationTaskInput>(RESOURCE);
export const useUpdateIrrigationTask = () =>
  useUpdateEntity<IrrigationTask, UpdateIrrigationTaskInput>(RESOURCE);
