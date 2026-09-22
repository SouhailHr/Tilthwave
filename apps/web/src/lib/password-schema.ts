import { z } from "zod";

/** The API's rule (min 8, max 72 bytes for bcrypt), stated once for every form that sets a password. */
export const passwordSchema = z
  .string()
  .min(8, "Use at least 8 characters")
  .max(72, "Use at most 72 characters");

export const PASSWORDS_MUST_MATCH: { message: string; path: string[] } = {
  message: "Passwords do not match",
  path: ["confirm_password"],
};

export const passwordsMatch = (v: { new_password: string; confirm_password: string }) =>
  v.new_password === v.confirm_password;
