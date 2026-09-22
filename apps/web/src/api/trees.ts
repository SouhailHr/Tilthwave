import { useCreateEntity, useUpdateEntity } from "@/api/_entity";
import type { CreateTreeInput, Tree, UpdateTreeInput } from "@/types/tree";

const RESOURCE = "trees";

// Thin typed facades over _entity.ts: EntityTable/EntityCrudPage already get list and delete
// generically from the resource string, so these two are all that's left.
export const useCreateTree = () =>
  useCreateEntity<Tree, CreateTreeInput>(RESOURCE);
export const useUpdateTree = () =>
  useUpdateEntity<Tree, UpdateTreeInput>(RESOURCE);
