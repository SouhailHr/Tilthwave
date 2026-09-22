"use client";

import {
  Activity,
  AlertTriangle,
  Droplets,
  Radio,
  Sprout,
} from "lucide-react";

import { useDashboardSummary } from "@/api/dashboard";
import type { DashboardSummary } from "@/types/dashboard";

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

// This page used to fan out seven polling queries - six paginated lists sampled at 100 rows
// each plus the farm stats - and count every status breakdown client-side inside that sample,
// which was silently wrong as soon as a table grew past 100 rows. /dashboard/summary computes
// every count in the database (scoped to the caller's farm like every other read) in one trip.

function sensorEntries(s: DashboardSummary["sensors"]): BreakdownEntry[] {
  return [
    { label: "Active", value: s.active, tone: "field" },
    { label: "Inactive", value: s.inactive, tone: "muted" },
    { label: "Unknown", value: s.unknown, tone: "muted" },
  ];
}

function actuatorEntries(
  a: DashboardSummary["water_sources"] | DashboardSummary["water_switchers"],
): BreakdownEntry[] {
  return [
    { label: "On", value: a.On, tone: "field" },
    { label: "Off", value: a.Off, tone: "muted" },
    { label: "Error", value: a.Error, tone: "harvest" },
  ];
}

function taskEntries(t: DashboardSummary["irrigation_tasks"]): BreakdownEntry[] {
  return [
    { label: "Pending", value: t.pending, tone: "muted" },
    { label: "In progress", value: t["in progress"], tone: "pulse" },
    { label: "Completed", value: t.completed, tone: "field" },
    { label: "Canceled", value: t.canceled, tone: "harvest" },
  ];
}

export default function HomePage() {
  const { data, isPending, error } = useDashboardSummary();

  const totalAlerts = (data?.water_sources.Error ?? 0) + (data?.water_switchers.Error ?? 0);
  const farm = data?.farm ?? null;

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

      {error ? (
        <div className="rounded-md border border-harvest/40 bg-harvest/10 px-4 py-3 text-sm text-loam">
          <span className="font-medium">Dashboard data failed to load.</span>{" "}
          {error.message}
        </div>
      ) : null}

      {/* Hero stats */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <DashboardStatCard
          label="Sensors live"
          value={data?.sensors.active ?? 0}
          hint={`of ${data?.sensors.total ?? 0} total`}
          icon={Radio}
          tone="pulse"
          isPending={isPending}
        />
        <DashboardStatCard
          label="Active tasks"
          value={data?.irrigation_tasks["in progress"] ?? 0}
          hint={`of ${data?.irrigation_tasks.total ?? 0} total`}
          icon={Activity}
          tone="loam"
          isPending={isPending}
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
          isPending={isPending}
        />
      </div>

      {/* Status breakdowns */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <StatusBreakdownCard
          title="Sensors"
          href="/sensors"
          entries={data ? sensorEntries(data.sensors) : []}
          total={data?.sensors.total ?? 0}
          isPending={isPending}
        />
        <StatusBreakdownCard
          title="Water sources"
          href="/water-sources"
          entries={data ? actuatorEntries(data.water_sources) : []}
          total={data?.water_sources.total ?? 0}
          isPending={isPending}
        />
        <StatusBreakdownCard
          title="Water switchers"
          href="/water-switchers"
          entries={data ? actuatorEntries(data.water_switchers) : []}
          total={data?.water_switchers.total ?? 0}
          isPending={isPending}
        />
        <StatusBreakdownCard
          title="Irrigation tasks"
          href="/irrigation-tasks"
          entries={data ? taskEntries(data.irrigation_tasks) : []}
          total={data?.irrigation_tasks.total ?? 0}
          isPending={isPending}
        />
      </div>

      {/* Farm overview with consumption chart */}
      {farm ? (
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-3">
            <div>
              <CardTitle>{farm.farm_name}</CardTitle>
              <CardDescription>Water consumption · this year</CardDescription>
            </div>
            <div className="grid grid-flow-col gap-4 text-center text-xs">
              <FarmStat label="Zones" value={farm.total_zones} isPending={isPending} />
              <FarmStat label="Trees" value={farm.total_trees} isPending={isPending} />
              <FarmStat
                label="Sources"
                value={farm.total_water_sources}
                isPending={isPending}
              />
              <FarmStat
                label="Switchers"
                value={farm.total_water_switchers}
                isPending={isPending}
              />
            </div>
          </CardHeader>
          <CardContent>
            {isPending ? (
              <Skeleton className="h-40 w-full" />
            ) : (
              <WaterConsumptionChart data={farm.chart_data} />
            )}
          </CardContent>
        </Card>
      ) : null}

      {/* Footprint + activity */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <div className="grid gap-3 sm:grid-cols-2 lg:col-span-1 lg:grid-cols-1">
          <DashboardStatCard
            label="Farms"
            value={data?.farms.total ?? 0}
            icon={Sprout}
            isPending={isPending}
          />
          <DashboardStatCard
            label="Zones"
            value={data?.zones.total ?? 0}
            icon={Droplets}
            isPending={isPending}
          />
        </div>
        <div className="lg:col-span-2">
          <RecentActivityCard tasks={data?.recent_tasks ?? []} isPending={isPending} />
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
