import type { FarmStats } from "@/types/farm";
import type { IrrigationTask } from "@/types/irrigation-task";

/** Shape of GET /dashboard/summary/: every count the home page shows, computed server-side. */
export interface DashboardSummary {
  sensors: { total: number; active: number; inactive: number; unknown: number };
  water_sources: { total: number; On: number; Off: number; Error: number };
  water_switchers: { total: number; On: number; Off: number; Error: number };
  irrigation_tasks: {
    total: number;
    pending: number;
    "in progress": number;
    completed: number;
    canceled: number;
  };
  /** Newest first, at most a handful. */
  recent_tasks: IrrigationTask[];
  farms: { total: number };
  zones: { total: number };
  /** The caller's farm with its counts and this year's consumption per month; null if they have none. */
  farm: ({ farm_name: string } & FarmStats) | null;
}
