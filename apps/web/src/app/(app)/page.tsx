"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Droplets,
  Radio,
  Sprout,
} from "lucide-react";

import { fetchIrrigationTasks } from "@/api/irrigation-tasks";
import { fetchSensors } from "@/api/sensors";
import { fetchWaterSources } from "@/api/water-sources";
import { fetchWaterSwitchers } from "@/api/water-switchers";
import { fetchFarms, useFarmStats } from "@/api/farms";
import { fetchZones } from "@/api/zones";
import { entityListKey } from "@/api/_entity";
import { REFRESH_MS, SAMPLE_SIZE } from "@/api/constants";
import type { ApiError } from "@/api/errors";
import type { Paginated } from "@/types/pagination";
import type { Sensor } from "@/types/sensor";
import type { WaterSource } from "@/types/water-source";
import type { WaterSwitcher } from "@/types/water-switcher";
import type {
  IrrigationTask,
  IrrigationTaskStatus,
} from "@/types/irrigation-task";
import type { Farm } from "@/types/farm";
import type { Zone } from "@/types/zone";

import { DashboardStatCard } from "@/components/dashboard-stat-card";
import {
  StatusBreakdownCard,
  type BreakdownEntry,
} from "@/components/status-breakdown-card";
import { RecentActivityCard } from "@/components/recent-activity-card";
import { WaterConsumptionChart } from "@/components/water-consumption-chart";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const sampleParams = { size: SAMPLE_SIZE };

function useLivePage<T>(
  queryKey: readonly unknown[],
  fetcher: (params: { size: number }) => Promise<Paginated<T>>,
) {
  return useQuery<Paginated<T>, ApiError>({
    queryKey,
    queryFn: () => fetcher(sampleParams),
    refetchInterval: REFRESH_MS,
  });
}

function countBy<T, K extends string>(
  items: T[] | undefined,
  pickKey: (item: T) => K | null | undefined,
): Record<K, number> {
  const out = {} as Record<K, number>;
  if (!items) return out;
  for (const item of items) {
    const key = pickKey(item);
    if (key == null) continue;
    out[key] = (out[key] ?? 0) + 1;
  }
  return out;
}

export default function HomePage() {
  const sensors = useLivePage<Sensor>(
    entityListKey("sensors", sampleParams),
    fetchSensors,
  );
  const waterSources = useLivePage<WaterSource>(
    entityListKey("water-sources", sampleParams),
    fetchWaterSources,
  );
  const waterSwitchers = useLivePage<WaterSwitcher>(
    entityListKey("water-switchers", sampleParams),
    fetchWaterSwitchers,
  );
  const tasks = useLivePage<IrrigationTask>(
    entityListKey("irrigation-tasks", sampleParams),
    fetchIrrigationTasks,
  );
  const farms = useLivePage<Farm>(
    entityListKey("farms", sampleParams),
    fetchFarms,
  );
  const zones = useLivePage<Zone>(
    entityListKey("zones", sampleParams),
    fetchZones,
  );

  const primaryFarmName = farms.data?.items[0]?.farm_name ?? null;
  const farmStats = useFarmStats(primaryFarmName);

  const sensorBreakdown = useMemo<{
    entries: BreakdownEntry[];
    activeCount: number;
  }>(() => {
    const items = sensors.data?.items;
    const counts = countBy(items, (s) =>
      s.is_active === true ? "active" : s.is_active === false ? "inactive" : "unknown",
    );
    return {
      activeCount: counts.active ?? 0,
      entries: [
        { label: "Active", value: counts.active ?? 0, tone: "field" },
        { label: "Inactive", value: counts.inactive ?? 0, tone: "muted" },
        { label: "Unknown", value: counts.unknown ?? 0, tone: "muted" },
      ],
    };
  }, [sensors.data]);

  const waterSourceBreakdown = useMemo<{
    entries: BreakdownEntry[];
    errorCount: number;
  }>(() => {
    const counts = countBy(waterSources.data?.items, (ws) => ws.status);
    return {
      errorCount: counts.Error ?? 0,
      entries: [
        { label: "On", value: counts.On ?? 0, tone: "field" },
        { label: "Off", value: counts.Off ?? 0, tone: "muted" },
        { label: "Error", value: counts.Error ?? 0, tone: "harvest" },
      ],
    };
  }, [waterSources.data]);

  const waterSwitcherBreakdown = useMemo<{
    entries: BreakdownEntry[];
    errorCount: number;
  }>(() => {
    const counts = countBy(waterSwitchers.data?.items, (sw) => sw.status);
    return {
      errorCount: counts.Error ?? 0,
      entries: [
        { label: "On", value: counts.On ?? 0, tone: "field" },
        { label: "Off", value: counts.Off ?? 0, tone: "muted" },
        { label: "Error", value: counts.Error ?? 0, tone: "harvest" },
      ],
    };
  }, [waterSwitchers.data]);

  const taskBreakdown = useMemo<{
    entries: BreakdownEntry[];
    activeCount: number;
  }>(() => {
    const counts = countBy<IrrigationTask, IrrigationTaskStatus>(
      tasks.data?.items,
      (t) => t.status,
    );
    return {
      activeCount: counts["in progress"] ?? 0,
      entries: [
        { label: "Pending", value: counts.pending ?? 0, tone: "muted" },
        { label: "In progress", value: counts["in progress"] ?? 0, tone: "pulse" },
        { label: "Completed", value: counts.completed ?? 0, tone: "field" },
        { label: "Canceled", value: counts.canceled ?? 0, tone: "harvest" },
      ],
    };
  }, [tasks.data]);

  const recentTasks = useMemo<IrrigationTask[]>(() => {
    const items = tasks.data?.items ?? [];
    return [...items].sort((a, b) => b.id - a.id).slice(0, 6);
  }, [tasks.data]);

  const totalAlerts =
    waterSourceBreakdown.errorCount + waterSwitcherBreakdown.errorCount;

  const liveSensors = sensorBreakdown.activeCount;
  const activeTasks = taskBreakdown.activeCount;

  const queryErrors = [
    sensors.error,
    waterSources.error,
    waterSwitchers.error,
    tasks.error,
    farms.error,
    zones.error,
    farmStats.error,
  ].filter((e): e is ApiError => e != null);
  const firstError = queryErrors[0];

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold tracking-tight">
          Home
        </h1>
        <p className="text-sm text-muted-foreground">
          Where farms speak. Fields listen.
        </p>
      </div>

      {firstError ? (
        <div className="rounded-md border border-harvest/40 bg-harvest/10 px-4 py-3 text-sm text-loam">
          <span className="font-medium">Some data failed to load.</span>{" "}
          {firstError.message}
          {queryErrors.length > 1 ? (
            <span className="text-muted-foreground">
              {" "}
              (and {queryErrors.length - 1} more)
            </span>
          ) : null}
        </div>
      ) : null}

      {/* Hero stats */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <DashboardStatCard
          label="Sensors live"
          value={liveSensors}
          hint={`of ${sensors.data?.total ?? 0} total`}
          icon={Radio}
          tone="pulse"
          isPending={sensors.isPending}
        />
        <DashboardStatCard
          label="Active tasks"
          value={activeTasks}
          hint={`of ${tasks.data?.total ?? 0} total`}
          icon={Activity}
          tone="loam"
          isPending={tasks.isPending}
        />
        <DashboardStatCard
          label="Alerts"
          value={totalAlerts}
          hint={
            totalAlerts === 0
              ? "All systems nominal"
              : "Devices in error state"
          }
          icon={AlertTriangle}
          tone={totalAlerts > 0 ? "harvest" : "default"}
          isPending={waterSources.isPending || waterSwitchers.isPending}
        />
      </div>

      {/* Status breakdowns */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <StatusBreakdownCard
          title="Sensors"
          href="/sensors"
          entries={sensorBreakdown.entries}
          total={sensors.data?.total ?? 0}
          isPending={sensors.isPending}
        />
        <StatusBreakdownCard
          title="Water sources"
          href="/water-sources"
          entries={waterSourceBreakdown.entries}
          total={waterSources.data?.total ?? 0}
          isPending={waterSources.isPending}
        />
        <StatusBreakdownCard
          title="Water switchers"
          href="/water-switchers"
          entries={waterSwitcherBreakdown.entries}
          total={waterSwitchers.data?.total ?? 0}
          isPending={waterSwitchers.isPending}
        />
        <StatusBreakdownCard
          title="Irrigation tasks"
          href="/irrigation-tasks"
          entries={taskBreakdown.entries}
          total={tasks.data?.total ?? 0}
          isPending={tasks.isPending}
        />
      </div>

      {/* Farm overview with consumption chart */}
      {primaryFarmName ? (
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-3">
            <div>
              <CardTitle>{primaryFarmName}</CardTitle>
              <CardDescription>Water consumption · this year</CardDescription>
            </div>
            <div className="grid grid-flow-col gap-4 text-center text-xs">
              <FarmStat
                label="Zones"
                value={farmStats.data?.total_zones}
                isPending={farmStats.isPending}
              />
              <FarmStat
                label="Trees"
                value={farmStats.data?.total_trees}
                isPending={farmStats.isPending}
              />
              <FarmStat
                label="Sources"
                value={farmStats.data?.total_water_sources}
                isPending={farmStats.isPending}
              />
              <FarmStat
                label="Switchers"
                value={farmStats.data?.total_water_switchers}
                isPending={farmStats.isPending}
              />
            </div>
          </CardHeader>
          <CardContent>
            {farmStats.isPending ? (
              <Skeleton className="h-40 w-full" />
            ) : (
              <WaterConsumptionChart data={farmStats.data?.chart_data} />
            )}
          </CardContent>
        </Card>
      ) : null}

      {/* Footprint + activity */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <div className="grid gap-3 sm:grid-cols-2 lg:col-span-1 lg:grid-cols-1">
          <DashboardStatCard
            label="Farms"
            value={farms.data?.total ?? 0}
            icon={Sprout}
            isPending={farms.isPending}
          />
          <DashboardStatCard
            label="Zones"
            value={zones.data?.total ?? 0}
            icon={Droplets}
            isPending={zones.isPending}
          />
        </div>
        <div className="lg:col-span-2">
          <RecentActivityCard tasks={recentTasks} isPending={tasks.isPending} />
        </div>
      </div>
    </div>
  );
}

function FarmStat({
  label,
  value,
  isPending,
}: {
  label: string;
  value: number | undefined;
  isPending: boolean;
}) {
  return (
    <div className="grid gap-0.5">
      <span className="text-muted-foreground uppercase tracking-wide">
        {label}
      </span>
      {isPending ? (
        <Skeleton className="mx-auto h-5 w-8" />
      ) : (
        <span className="font-heading text-lg font-semibold tabular-nums">
          {value ?? 0}
        </span>
      )}
    </div>
  );
}