import { api } from "@/api/client";
import { useCreateEntity, useUpdateEntity } from "@/api/_entity";
import type {
  CreateTreeInput,
  Tree,
  UpdateTreeInput,
} from "@/types/tree";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "trees";
const PATH = `/${RESOURCE}`;

// The dashboard polls this directly (bypasses the generic EntityTable/EntityCrudPage path, so
// it isn't covered by _entity.ts's fetchEntityList call site). Everything else this module used
// to duplicate - fetchTree, createTree, updateTree, deleteTree, useTrees, useTree, useDeleteTree
// - had zero callers: EntityTable/EntityCrudPage already get list and delete generically from
// _entity.ts given just the resource string.
export function fetchTrees(params: ListParams = {}) {
  return api.get<Paginated<Tree>>(`${PATH}/`, { params }).then((r) => r.data);
}

export const useCreateTree = () =>
  useCreateEntity<Tree, CreateTreeInput>(RESOURCE);
export const useUpdateTree = () =>
  useUpdateEntity<Tree, UpdateTreeInput>(RESOURCE);
