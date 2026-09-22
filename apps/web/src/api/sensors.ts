import { api } from "@/api/client";
import { useCreateEntity, useEntityList, useUpdateEntity } from "@/api/_entity";
import type {
  CreateSensorInput,
  Sensor,
  UpdateSensorInput,
} from "@/types/sensor";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "sensors";
const PATH = `/${RESOURCE}`;

// The dashboard polls this directly (bypasses the generic EntityTable/EntityCrudPage path, so
// it isn't covered by _entity.ts's fetchEntityList call site). Everything else this module used
// to duplicate - fetchSensor, createSensor, updateSensor, deleteSensor, useSensor,
// useDeleteSensor - had zero callers: EntityTable/EntityCrudPage already get list and delete
// generically from _entity.ts given just the resource string. useSensors survives because
// app-shell.tsx uses it directly for its sidebar count, outside the CRUD-page path.
export function fetchSensors(params: ListParams = {}) {
  return api.get<Paginated<Sensor>>(`${PATH}/`, { params }).then((r) => r.data);
}

export const useSensors = (params: ListParams = {}) =>
  useEntityList<Sensor>(RESOURCE, params);
export const useCreateSensor = () =>
  useCreateEntity<Sensor, CreateSensorInput>(RESOURCE);
export const useUpdateSensor = () =>
  useUpdateEntity<Sensor, UpdateSensorInput>(RESOURCE);
