import { api } from "@/api/client";
import { useCreateEntity, useUpdateEntity } from "@/api/_entity";
import type {
  CreateWaterSourceInput,
  UpdateWaterSourceInput,
  WaterSource,
} from "@/types/water-source";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "water-sources";
const PATH = `/${RESOURCE}`;

// The dashboard polls this directly (bypasses the generic EntityTable/EntityCrudPage path, so
// it isn't covered by _entity.ts's fetchEntityList call site). Everything else this module used
// to duplicate - fetchWaterSource, createWaterSource, updateWaterSource, deleteWaterSource,
// useWaterSources, useWaterSource, useDeleteWaterSource - had zero callers:
// EntityTable/EntityCrudPage already get list and delete generically from _entity.ts given just
// the resource string.
export function fetchWaterSources(params: ListParams = {}) {
  return api
    .get<Paginated<WaterSource>>(`${PATH}/`, { params })
    .then((r) => r.data);
}

export const useCreateWaterSource = () =>
  useCreateEntity<WaterSource, CreateWaterSourceInput>(RESOURCE);
export const useUpdateWaterSource = () =>
  useUpdateEntity<WaterSource, UpdateWaterSourceInput>(RESOURCE);
