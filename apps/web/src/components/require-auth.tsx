"use client";

import { ReactNode, useEffect, useSyncExternalStore } from "react";
import { usePathname, useRouter } from "next/navigation";
import { isAuthenticated } from "@/api/auth";
import { subscribeToTokenChanges } from "@/utils/tokenStorage";
import { subscribe } from "@/lib/eventBus";
import { safeRedirect } from "@/utils/safeRedirect";

export function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  // The server (and the first client render, which must match it to avoid a hydration
  // mismatch) has no access to localStorage, so this is always "false" on that first pass,
  // even for an already-authenticated user refreshing the page. React notices the mismatch
  // on its own and schedules a corrective re-render, but that correction lands one render
  // AFTER this component's own effects below run for the first time. The redirect effect
  // must not trust this value directly; see the comment there.
  const authed = useSyncExternalStore(
    subscribeToTokenChanges,
    () => isAuthenticated(),
    () => false,
  );

  useEffect(() => {
    return subscribe((event) => {
      if (event.type !== "auth:expired") return;
      const target = safeRedirect(event.redirect ?? pathname);
      const params = new URLSearchParams({ redirect: target, expired: "1" });
      router.replace(`/login?${params.toString()}`);
    });
  }, [router, pathname]);

  useEffect(() => {
    // Re-check freshly instead of trusting `authed`: an effect body only ever runs on the
    // client, so this always reflects the real, current value, even on the very first render
    // after hydration where `authed` above is still React's stale server-snapshot
    // placeholder. Without this, refreshing an already-authenticated page bounced straight
    // back to /login, because the redirect fired off that placeholder before React's own
    // corrective re-render for `authed` had a chance to land.
    if (!isAuthenticated()) {
      const target = safeRedirect(pathname);
      router.replace(`/login?redirect=${encodeURIComponent(target)}`);
    }
  }, [authed, pathname, router]);

  if (!authed) return null;
  return <>{children}</>;
}