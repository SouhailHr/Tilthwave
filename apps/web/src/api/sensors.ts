import { useCreateEntity, useEntityList, useUpdateEntity } from "@/api/_entity";
import type { CreateSensorInput, Sensor, UpdateSensorInput } from "@/types/sensor";
import type { ListParams } from "@/types/pagination";

const RESOURCE = "sensors";

// Thin typed facades over _entity.ts: EntityTable/EntityCrudPage already get list and delete
// generically from the resource string, and the dashboard reads /dashboard/summary instead of
// polling the list here. useSensors survives because app-shell.tsx uses it directly for its
// sidebar count, outside the CRUD-page path.
export const useSensors = (params: ListParams = {}) =>
  useEntityList<Sensor>(RESOURCE, params);
export const useCreateSensor = () =>
  useCreateEntity<Sensor, CreateSensorInput>(RESOURCE);
export const useUpdateSensor = () =>
  useUpdateEntity<Sensor, UpdateSensorInput>(RESOURCE);
