"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[app:error]", error);
  }, [error]);

  return (
    <main className="flex flex-1 items-center justify-center p-6">
      <div className="grid max-w-md gap-4 text-center">
        <h1 className="font-heading text-2xl font-semibold">Something went wrong</h1>
        <p className="text-sm text-muted-foreground">
          The page hit an unexpected error.
          {error.digest ? (
            <>
              <br />
              <span className="font-mono text-xs">ref: {error.digest}</span>
            </>
          ) : null}
        </p>
        <div className="flex justify-center gap-2">
          <Button onClick={reset}>Try again</Button>
        </div>
      </div>
    </main>
  );
}