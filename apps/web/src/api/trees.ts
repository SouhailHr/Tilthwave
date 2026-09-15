import { api } from "@/api/client";
import {
  useCreateEntity,
  useDeleteEntity,
  useEntity,
  useEntityList,
  useUpdateEntity,
} from "@/api/_entity";
import type {
  CreateTreeInput,
  Tree,
  UpdateTreeInput,
} from "@/types/tree";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "trees";
const PATH = `/${RESOURCE}`;

export function fetchTrees(params: ListParams = {}) {
  return api.get<Paginated<Tree>>(`${PATH}/`, { params }).then((r) => r.data);
}

export function fetchTree(id: number | string) {
  return api.get<Tree>(`${PATH}/${id}/`).then((r) => r.data);
}

export function createTree(input: CreateTreeInput) {
  return api.post<Tree>(`${PATH}/`, input).then((r) => r.data);
}

export function updateTree(id: number | string, input: UpdateTreeInput) {
  return api.patch<Tree>(`${PATH}/${id}/`, input).then((r) => r.data);
}

export function deleteTree(id: number | string) {
  return api.delete(`${PATH}/${id}/`).then(() => id);
}

export const useTrees = (params: ListParams = {}) =>
  useEntityList<Tree>(RESOURCE, params);
export const useTree = (id: number | string | null | undefined) =>
  useEntity<Tree>(RESOURCE, id);
export const useCreateTree = () =>
  useCreateEntity<Tree, CreateTreeInput>(RESOURCE);
export const useUpdateTree = () =>
  useUpdateEntity<Tree, UpdateTreeInput>(RESOURCE);
export const useDeleteTree = () => useDeleteEntity(RESOURCE);