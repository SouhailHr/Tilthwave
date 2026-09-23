import * as z from "zod";

/**
 * The API's rule, stated once for every form that sets a password: at least 8 characters, and at
 * most 72 *bytes*, which is bcrypt's limit and what the API checks. A 40-character Cyrillic or CJK
 * password is 120 bytes, so the length is measured encoded, not in characters.
 */
export const passwordSchema = z
  .string()
  .min(8, "Use at least 8 characters")
  .refine((v) => new TextEncoder().encode(v).length <= 72, "Use at most 72 bytes (about 72 Latin characters)");

export const PASSWORDS_MUST_MATCH: { message: string; path: string[] } = {
  message: "Passwords do not match",
  path: ["confirm_password"],
};

export const passwordsMatch = (v: { new_password: string; confirm_password: string }) =>
  v.new_password === v.confirm_password;
