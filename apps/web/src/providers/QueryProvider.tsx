"use client";

import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { ReactNode, useState } from "react";

import { toApiError, type ApiError } from "@/api/errors";
import { Toaster } from "@/components/ui/sonner";
import { emit } from "@/lib/eventBus";

const ReactQueryDevtools = dynamic(
  () =>
    import("@tanstack/react-query-devtools").then((m) => m.ReactQueryDevtools),
  { ssr: false },
);

function reportError(err: unknown, source: "query" | "mutation") {
  const apiError: ApiError = toApiError(err);
  emit({ type: "api:error", error: apiError, source });
  if (process.env.NODE_ENV !== "production") {
    console.error(`[react-query:${source}]`, apiError);
  }
}

export function QueryProvider({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({
          onError: (err) => reportError(err, "query"),
        }),
        mutationCache: new MutationCache({
          onError: (err) => reportError(err, "mutation"),
        }),
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      {children}
      <Toaster richColors position="top-right" />
      {process.env.NODE_ENV === "development" ? (
        <ReactQueryDevtools initialIsOpen={false} />
      ) : null}
    </QueryClientProvider>
  );
}