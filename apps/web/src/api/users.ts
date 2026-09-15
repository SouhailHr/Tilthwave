import { api } from "@/api/client";
import {
  useCreateEntity,
  useDeleteEntity,
  useEntity,
  useEntityList,
  useUpdateEntity,
} from "@/api/_entity";
import type {
  CreateUserInput,
  UpdateUserInput,
  User,
} from "@/types/user";
import type { ListParams, Paginated } from "@/types/pagination";

const RESOURCE = "users";
const PATH = `/${RESOURCE}`;

export function fetchUsers(params: ListParams = {}) {
  return api.get<Paginated<User>>(`${PATH}/`, { params }).then((r) => r.data);
}

export function fetchUser(id: number | string) {
  return api.get<User>(`${PATH}/${id}/`).then((r) => r.data);
}

export const useUsers = (params: ListParams = {}) =>
  useEntityList<User>(RESOURCE, params);
export const useUser = (id: number | string | null | undefined) =>
  useEntity<User>(RESOURCE, id);
export const useCreateUser = () =>
  useCreateEntity<User, CreateUserInput>(RESOURCE);
export const useUpdateUser = () =>
  useUpdateEntity<User, UpdateUserInput>(RESOURCE);
export const useDeleteUser = () => useDeleteEntity(RESOURCE);