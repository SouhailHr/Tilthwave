export const USER_ROLES = ["admin", "owner", "worker", "engineer"] as const;
export type UserRole = (typeof USER_ROLES)[number];

export interface User {
  id: number;
  username: string;
  email: string;
  phone_number: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  farm_name: string | null;
  is_superuser: boolean | null;
}

export interface CreateUserInput {
  username: string;
  email: string;
  phone_number: string;
  text_password: string;
  password?: string | null;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  farm_name?: string | null;
}

// What PATCH /users/{id} accepts (UserUpdate has extra="forbid"): no username, farm, password or
// superuser flag (derived from the role; not accepted on create either). A password changes through Settings or the reset link.
export type UpdateUserInput = Partial<
  Pick<CreateUserInput, "email" | "phone_number" | "first_name" | "last_name" | "role" | "is_active">
>;