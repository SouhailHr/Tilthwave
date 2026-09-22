import { api } from "@/api/client";
import { useCreateEntity, useUpdateEntity } from "@/api/_entity";
import type {
  CreateZoneInput,
  UpdateZoneInput,
  Zone,
} from "@/types/zone";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "zones";
const PATH = `/${RESOURCE}`;

// The dashboard polls this directly (bypasses the generic EntityTable/EntityCrudPage path, so
// it isn't covered by _entity.ts's fetchEntityList call site). Everything else this module used
// to duplicate - fetchZone, createZone, updateZone, deleteZone, useZones, useZone, useDeleteZone
// - had zero callers: EntityTable/EntityCrudPage already get list and delete generically from
// _entity.ts given just the resource string (see zones/page.tsx passing resource="zones").
export function fetchZones(params: ListParams = {}) {
  return api.get<Paginated<Zone>>(`${PATH}/`, { params }).then((r) => r.data);
}

export const useCreateZone = () =>
  useCreateEntity<Zone, CreateZoneInput>(RESOURCE);
export const useUpdateZone = () =>
  useUpdateEntity<Zone, UpdateZoneInput>(RESOURCE);
