import type { User } from "@/types/user";

/** What a user may change about themselves. Role, farm and active flag are an admin's. */
export type ProfileUpdateInput = Partial<
  Pick<User, "email" | "phone_number" | "first_name" | "last_name">
>;

export interface PasswordChangeInput {
  current_password: string;
  new_password: string;
}

/** One signed-in session, as GET /account/sessions lists them (live ones only). */
export interface UserSession {
  id: number;
  channel: "cookie" | "header";
  user_agent: string | null;
  client_ip: string | null;
  created_date: string;
  last_seen: string;
  expires_at: string;
  /** The session making the request. */
  current: boolean;
}
