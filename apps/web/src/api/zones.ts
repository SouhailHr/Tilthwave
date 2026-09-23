import { useCreateEntity, useUpdateEntity } from "@/api/entity-queries";
import type { CreateZoneInput, UpdateZoneInput, Zone } from "@/types/zone";

const RESOURCE = "zones";

// Thin typed facades over entity-queries.ts: EntityTable/EntityCrudPage already get list and delete
// generically from the resource string, and the dashboard reads /dashboard/summary instead of
// polling the list here, so these two are all that's left.
export const useCreateZone = () =>
  useCreateEntity<Zone, CreateZoneInput>(RESOURCE);
export const useUpdateZone = () =>
  useUpdateEntity<Zone, UpdateZoneInput>(RESOURCE);
