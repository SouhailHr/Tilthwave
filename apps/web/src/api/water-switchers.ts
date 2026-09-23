import { useCreateEntity, useUpdateEntity } from "@/api/entity-queries";
import type {
  CreateWaterSwitcherInput,
  UpdateWaterSwitcherInput,
  WaterSwitcher,
} from "@/types/water-switcher";

const RESOURCE = "water-switchers";

// Thin typed facades over entity-queries.ts: EntityTable/EntityCrudPage already get list and delete
// generically from the resource string, and the dashboard reads /dashboard/summary instead of
// polling the list here, so these two are all that's left.
export const useCreateWaterSwitcher = () =>
  useCreateEntity<WaterSwitcher, CreateWaterSwitcherInput>(RESOURCE);
export const useUpdateWaterSwitcher = () =>
  useUpdateEntity<WaterSwitcher, UpdateWaterSwitcherInput>(RESOURCE);
