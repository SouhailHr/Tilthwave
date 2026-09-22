import { useCreateEntity, useUpdateEntity } from "@/api/_entity";
import type { CreateFarmInput, Farm, UpdateFarmInput } from "@/types/farm";

const RESOURCE = "farms";

// Thin typed facades over _entity.ts: EntityTable/EntityCrudPage already get list and delete
// generically from the resource string, and the dashboard reads the farm's stats from
// /dashboard/summary instead of the separate /farms/stats/{name} query it used to make here.
// useUpdateFarm used to be a hand-rolled mutation that only invalidated the root key; the
// generic one invalidates root and detail, a strict superset, with the same PATCH underneath.
export const useCreateFarm = () =>
  useCreateEntity<Farm, CreateFarmInput>(RESOURCE);
export const useUpdateFarm = () =>
  useUpdateEntity<Farm, UpdateFarmInput>(RESOURCE);
