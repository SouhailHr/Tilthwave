import { useCreateEntity, useUpdateEntity } from "@/api/entity-queries";
import type { CreateUserInput, UpdateUserInput, User } from "@/types/user";

// The users page reads its list and rows through EntityCrudPage; only the two mutations need a
// typed facade here, like the other resources.
const RESOURCE = "users";

export const useCreateUser = () => useCreateEntity<User, CreateUserInput>(RESOURCE);
export const useUpdateUser = () => useUpdateEntity<User, UpdateUserInput>(RESOURCE);
