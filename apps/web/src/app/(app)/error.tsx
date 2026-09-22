"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[app-segment:error]", error);
  }, [error]);

  return (
    <div className="grid gap-4 rounded-xl border border-destructive/40 bg-destructive/5 p-6">
      <div>
        <h2 className="font-heading text-lg font-semibold">
          This section couldn&apos;t load
        </h2>
        <p className="text-sm text-muted-foreground">
          {error.message || "Unexpected error"}
          {error.digest ? (
            <span className="block font-mono text-xs">ref: {error.digest}</span>
          ) : null}
        </p>
      </div>
      <div>
        <Button variant="outline" onClick={reset}>
          Retry
        </Button>
      </div>
    </div>
  );
}