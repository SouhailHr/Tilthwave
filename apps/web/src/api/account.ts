import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { sessionKey } from "@/api/auth";
import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import type { PasswordChangeInput, ProfileUpdateInput } from "@/types/account";
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
