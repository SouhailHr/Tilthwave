import { api } from "@/api/client";
import { useCreateEntity, useUpdateEntity } from "@/api/_entity";
import type {
  CreateWaterSwitcherInput,
  UpdateWaterSwitcherInput,
  WaterSwitcher,
} from "@/types/water-switcher";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "water-switchers";
const PATH = `/${RESOURCE}`;

// The dashboard polls this directly (bypasses the generic EntityTable/EntityCrudPage path, so
// it isn't covered by _entity.ts's fetchEntityList call site). Everything else this module used
// to duplicate - fetchWaterSwitcher, createWaterSwitcher, updateWaterSwitcher,
// deleteWaterSwitcher, useWaterSwitchers, useWaterSwitcher, useDeleteWaterSwitcher - had zero
// callers: EntityTable/EntityCrudPage already get list and delete generically from _entity.ts
// given just the resource string.
export function fetchWaterSwitchers(params: ListParams = {}) {
  return api
    .get<Paginated<WaterSwitcher>>(`${PATH}/`, { params })
    .then((r) => r.data);
}

export const useCreateWaterSwitcher = () =>
  useCreateEntity<WaterSwitcher, CreateWaterSwitcherInput>(RESOURCE);
export const useUpdateWaterSwitcher = () =>
  useUpdateEntity<WaterSwitcher, UpdateWaterSwitcherInput>(RESOURCE);
