import type { User } from "@/types/user";

/** What a user may change about themselves. Role, farm and active flag are an admin's. */
export type ProfileUpdateInput = Partial<
  Pick<User, "email" | "phone_number" | "first_name" | "last_name">
>;

export interface PasswordChangeInput {
  current_password: string;
  new_password: string;
}
