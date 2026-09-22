import { useCreateEntity, useUpdateEntity } from "@/api/_entity";
import type {
  CreateIrrigationTaskInput,
  IrrigationTask,
  UpdateIrrigationTaskInput,
} from "@/types/irrigation-task";

const RESOURCE = "irrigation-tasks";

// Thin typed facades over _entity.ts: EntityTable/EntityCrudPage already get list and delete
// generically from the resource string, and the dashboard reads /dashboard/summary instead of
// polling the list here, so these two are all that's left.
export const useCreateIrrigationTask = () =>
  useCreateEntity<IrrigationTask, CreateIrrigationTaskInput>(RESOURCE);
export const useUpdateIrrigationTask = () =>
  useUpdateEntity<IrrigationTask, UpdateIrrigationTaskInput>(RESOURCE);
