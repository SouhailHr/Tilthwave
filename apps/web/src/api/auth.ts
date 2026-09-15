import { jwtDecode } from "jwt-decode";
import { useMutation } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import {
  clearStoredToken,
  getStoredToken,
  setStoredToken,
} from "@/utils/tokenStorage";

export interface LoginPayload {
  username: string;
  password: string;
}

const loginResponseSchema = z.object({
  token: z.string().min(1),
});
export type LoginResponse = z.infer<typeof loginResponseSchema>;

const claimsSchema = z.object({
  user_id: z.number(),
  exp: z.number(),
});
export type JwtClaims = z.infer<typeof claimsSchema>;

let claimsCache: { token: string; claims: JwtClaims } | null = null;

function decodeClaims(token: string): JwtClaims | null {
  if (claimsCache && claimsCache.token === token) return claimsCache.claims;
  try {
    const parsed = claimsSchema.safeParse(jwtDecode(token));
    if (!parsed.success) return null;
    claimsCache = { token, claims: parsed.data };
    return parsed.data;
  } catch {
    return null;
  }
}

export function getCurrentUserId(): number | null {
  const token = getStoredToken();
  if (!token) return null;
  const claims = decodeClaims(token);
  if (!claims) return null;
  if (claims.exp * 1000 < Date.now()) return null;
  return claims.user_id;
}

export function enforceTokenFreshness(): boolean {
  const token = getStoredToken();
  if (!token) return false;
  const claims = decodeClaims(token);
  if (!claims || claims.exp * 1000 < Date.now()) {
    clearStoredToken();
    claimsCache = null;
    return false;
  }
  return true;
}

export function isAuthenticated(): boolean {
  return getCurrentUserId() !== null;
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const { data } = await api.post<unknown>("/auth/login/", payload);
  const parsed = loginResponseSchema.parse(data);
  setStoredToken(parsed.token);
  return parsed;
}

export function logout() {
  claimsCache = null;
  clearStoredToken();
}

export function useLogin() {
  return useMutation<LoginResponse, ApiError, LoginPayload>({
    mutationFn: login,
  });
}