import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { REFRESH_MS } from "@/api/constants";
import type { ApiError } from "@/api/errors";
import type { DashboardSummary } from "@/types/dashboard";

export const dashboardSummaryKey = ["dashboard", "summary"] as const;

export function fetchDashboardSummary() {
  return api.get<DashboardSummary>("/dashboard/summary/").then((r) => r.data);
}

/** One polling query in place of the seven the home page used to fan out. */
export function useDashboardSummary() {
  return useQuery<DashboardSummary, ApiError>({
    queryKey: dashboardSummaryKey,
    queryFn: fetchDashboardSummary,
    refetchInterval: REFRESH_MS,
  });
}
