import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { sessionKey } from "@/api/auth";
import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import type { PasswordChangeInput, ProfileUpdateInput, UserSession } from "@/types/account";
import type { User } from "@/types/user";

export const profileKey = ["account", "profile"] as const;

export function fetchProfile() {
  return api.get<User>("/account/profile").then((r) => r.data);
}

/** The signed-in user's own record: contact details, role, farm. */
export function useProfile() {
  return useQuery<User, ApiError>({ queryKey: profileKey, queryFn: fetchProfile });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation<User, ApiError, ProfileUpdateInput>({
    mutationFn: (input) => api.patch<User>("/account/profile", input).then((r) => r.data),
    onSuccess: (user) => {
      queryClient.setQueryData(profileKey, user);
      queryClient.invalidateQueries({ queryKey: sessionKey });
    },
  });
}

/**
 * The API re-issues this session's cookies in the response, so the user stays signed in here
 * while every other device is signed out. Nothing to do client-side but tell them.
 */
export function useChangePassword() {
  return useMutation<void, ApiError, PasswordChangeInput>({
    mutationFn: (input) => api.post("/account/password", input).then(() => undefined),
  });
}

// ---- sessions ------------------------------------------------------------------------------
// Server-side sessions: the API refuses a token whose session was ended, so revoking one here
// signs that device out at its next request, not when its token happens to expire.

export const sessionsKey = ["account", "sessions"] as const;

export function fetchSessions() {
  return api.get<{ items: UserSession[] }>("/account/sessions").then((r) => r.data.items);
}

export function useSessions() {
  return useQuery<UserSession[], ApiError>({ queryKey: sessionsKey, queryFn: fetchSessions });
}

/** End one of the caller's own sessions. Ending the current one is a logout. */
export function useRevokeSession() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, number>({
    mutationFn: (id) => api.delete(`/account/sessions/${id}`).then(() => undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sessionsKey }),
  });
}

/** Sign out everywhere else: every session but this one. Returns how many were ended. */
export function useRevokeOtherSessions() {
  const queryClient = useQueryClient();
  return useMutation<number, ApiError, void>({
    mutationFn: () => api.delete<{ revoked: number }>("/account/sessions").then((r) => r.data.revoked),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sessionsKey }),
  });
}
