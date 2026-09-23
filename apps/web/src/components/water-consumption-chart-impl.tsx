"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { cn } from "@/lib/utils";
import type { FarmStats } from "@/types/farm";

const MONTH_ORDER = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
] as const;

const MONTH_SHORT: Record<(typeof MONTH_ORDER)[number], string> = {
  January: "Jan",
  February: "Feb",
  March: "Mar",
  April: "Apr",
  May: "May",
  June: "Jun",
  July: "Jul",
  August: "Aug",
  September: "Sep",
  October: "Oct",
  November: "Nov",
  December: "Dec",
};

interface ChartPoint {
  month: string;
  fullMonth: string;
  /** null for a month that has not started: no bar, rather than a misleading zero. */
  value: number | null;
  current: boolean;
}

// 612 000 -> "612k", 1 250 000 -> "1.3M": the axis stays four characters wide.
const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });

interface WaterConsumptionChartProps {
  data: FarmStats["chart_data"] | undefined;
  unit?: string;
  className?: string;
}

export function WaterConsumptionChart({
  data,
  unit = "m³",
  className,
  now = new Date(),
}: WaterConsumptionChartProps & { now?: Date }) {
  const thisMonth = now.getMonth();
  const series = useMemo<ChartPoint[]>(() => {
    if (!data) return [];
    // The API reports the current calendar year: months after this one have not happened yet.
    return MONTH_ORDER.map((month, index) => ({
      month: MONTH_SHORT[month],
      fullMonth: month,
      value: index > thisMonth ? null : (data[month]?.Total ?? 0),
      current: index === thisMonth,
    }));
  }, [data, thisMonth]);

  const total = useMemo(
    () => series.reduce((acc, point) => acc + (point.value ?? 0), 0),
    [series],
  );

  if (series.length === 0) {
    return (
      <div className={cn("text-sm text-muted-foreground", className)}>
        No data.
      </div>
    );
  }

  return (
    <div className={cn("grid gap-3", className)}>
      <div className="flex items-baseline justify-between gap-4 text-sm">
        <span className="text-muted-foreground">Monthly total, {unit}</span>
        <span className="font-medium tabular-nums">
          {total.toLocaleString("en")} {unit} <span className="text-muted-foreground">this year</span>
        </span>
      </div>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={series} margin={{ top: 8, right: 4, left: 0, bottom: 0 }} barCategoryGap="22%">
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
            <XAxis
              dataKey="month"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }}
              tickMargin={8}
              interval={0}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }}
              tickFormatter={(value: number) => compact.format(value)}
              allowDecimals={false}
              width={40}
            />
            <Tooltip
              cursor={{ fill: "var(--color-muted)", opacity: 0.6 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const point = payload[0]?.payload as ChartPoint | undefined;
                if (!point || point.value === null) return null;
                return (
                  <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-md">
                    <div className="font-medium text-foreground">
                      {point.fullMonth}
                      {point.current ? " (so far)" : ""}
                    </div>
                    <div className="text-muted-foreground">
                      <span className="tabular-nums text-foreground">{point.value.toLocaleString("en")}</span> {unit}
                    </div>
                  </div>
                );
              }}
            />
            <Bar dataKey="value" radius={[6, 6, 0, 0]} isAnimationActive animationDuration={500}>
              {series.map((point) => (
                <Cell
                  key={point.month}
                  fill="var(--color-furrow)"
                  fillOpacity={point.current ? 1 : 0.55}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
