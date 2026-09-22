import { useCreateEntity, useUpdateEntity } from "@/api/_entity";
import type {
  CreateWaterSourceInput,
  UpdateWaterSourceInput,
  WaterSource,
} from "@/types/water-source";

const RESOURCE = "water-sources";

// Thin typed facades over _entity.ts: EntityTable/EntityCrudPage already get list and delete
// generically from the resource string, and the dashboard reads /dashboard/summary instead of
// polling the list here, so these two are all that's left.
export const useCreateWaterSource = () =>
  useCreateEntity<WaterSource, CreateWaterSourceInput>(RESOURCE);
export const useUpdateWaterSource = () =>
  useUpdateEntity<WaterSource, UpdateWaterSourceInput>(RESOURCE);
