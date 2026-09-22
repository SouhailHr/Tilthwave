import { useCreateEntity, useEntityList, useUpdateEntity } from "@/api/entity-queries";
import type { ListParams } from "@/types/pagination";
import type { CreateSensorInput, Sensor, UpdateSensorInput } from "@/types/sensor";

const RESOURCE = "sensors";

// Thin typed facades over entity-queries.ts: EntityTable/EntityCrudPage already get list and delete
// generically from the resource string, and the dashboard reads /dashboard/summary instead of
// polling the list here. useSensors survives because app-shell.tsx uses it directly for its
// sidebar count, outside the CRUD-page path.
export const useSensors = (params: ListParams = {}) =>
  useEntityList<Sensor>(RESOURCE, params);
export const useCreateSensor = () =>
  useCreateEntity<Sensor, CreateSensorInput>(RESOURCE);
export const useUpdateSensor = () =>
  useUpdateEntity<Sensor, UpdateSensorInput>(RESOURCE);
