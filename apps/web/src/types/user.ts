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
  is_superuser?: boolean | null;
}

export type UpdateUserInput = Partial<Omit<CreateUserInput, "username">>;