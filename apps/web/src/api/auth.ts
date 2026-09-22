import { isAxiosError } from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";

export interface LoginPayload {
  username: string;
  password: string;
}

// What GET /auth/me returns: the identity the API established from the session cookie, with
// role and farm from the database. The token itself is never visible here (httpOnly cookie).
const sessionSchema = z.object({
  user_id: z.number(),
  username: z.string(),
  role: z.string(),
  farm_name: z.string().nullable(),
  exp: z.number(),
});
export type Session = z.infer<typeof sessionSchema>;

export const sessionKey = ["auth", "me"] as const;

/** The signed-in identity, or null when the API answers 401 (nobody is signed in). */
export async function fetchSession(): Promise<Session | null> {
  try {
    const { data } = await api.get<unknown>("/auth/me");
    return sessionSchema.parse(data);
  } catch (err) {
    if (isAxiosError(err) && err.response?.status === 401) return null;
    throw err;
  }
}

export async function login(payload: LoginPayload): Promise<Session> {
  // use_cookie: the API answers with Set-Cookie and no token in the body. Nothing is stored
  // client-side; the browser holds the session and sends it on its own from here on.
  await api.post("/auth/login/", { ...payload, use_cookie: true });
  const session = await fetchSession();
  if (!session) throw new Error("Signed in, but the session cookie did not come back");
  return session;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}

/**
 * Whether (and who) the user is signed in as. Async by nature: the answer lives on the server,
 * behind a cookie this code cannot read, and React Query caches it for a minute.
 */
export function useSession() {
  return useQuery<Session | null, ApiError>({
    queryKey: sessionKey,
    queryFn: fetchSession,
    retry: false,
    staleTime: 60_000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation<Session, ApiError, LoginPayload>({
    mutationFn: login,
    onSuccess: (session) => queryClient.setQueryData(sessionKey, session),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, void>({
    mutationFn: logout,
    // Even if the request failed, the user asked to leave: forget the session locally.
    onSettled: () => queryClient.setQueryData(sessionKey, null),
  });
}
