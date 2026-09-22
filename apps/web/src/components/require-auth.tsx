"use client";

import { ReactNode, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { sessionKey, useSession } from "@/api/auth";
import { subscribe } from "@/lib/eventBus";
import { safeRedirect } from "@/utils/safeRedirect";

export function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();

  // The session is an httpOnly cookie the browser sends on its own, so JavaScript cannot read
  // it: "am I signed in" is a question for the server (GET /auth/me), cached by React Query.
  // Being async by construction also removes the old hydration race, where a synchronous check
  // fed an SSR placeholder of "false" to a redirect effect before the real value had landed:
  // isPending is true on the server and on the first client render alike, and nothing here
  // redirects until the probe has actually answered.
  const session = useSession();

  useEffect(() => {
    return subscribe((event) => {
      if (event.type !== "auth:expired") return;
      queryClient.setQueryData(sessionKey, null);
      const target = safeRedirect(event.redirect ?? pathname);
      const params = new URLSearchParams({ redirect: target, expired: "1" });
      router.replace(`/login?${params.toString()}`);
    });
  }, [queryClient, router, pathname]);

  // Only a definite "nobody is signed in" (the probe answered 401) redirects. A failed probe
  // (API unreachable) is not that: it renders nothing and ObservabilitySink toasts the error,
  // rather than bouncing a user who may well be signed in to the login page.
  const signedOut = session.isSuccess && session.data === null;
  useEffect(() => {
    if (signedOut) {
      const target = safeRedirect(pathname);
      router.replace(`/login?redirect=${encodeURIComponent(target)}`);
    }
  }, [signedOut, pathname, router]);

  if (!session.data) return null;
  return <>{children}</>;
}
