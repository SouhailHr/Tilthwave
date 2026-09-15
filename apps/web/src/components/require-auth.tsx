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
    if (!authed) {
      const target = safeRedirect(pathname);
      router.replace(`/login?redirect=${encodeURIComponent(target)}`);
    }
  }, [authed, pathname, router]);

  if (!authed) return null;
  return <>{children}</>;
}