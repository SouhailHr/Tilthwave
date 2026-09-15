"use client";

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

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
  value: number;
}

interface WaterConsumptionChartProps {
  data: FarmStats["chart_data"] | undefined;
  unit?: string;
  className?: string;
}

export function WaterConsumptionChart({
  data,
  unit = "m³",
  className,
}: WaterConsumptionChartProps) {
  const series = useMemo<ChartPoint[]>(() => {
    if (!data) return [];
    return MONTH_ORDER.map((month) => ({
      month: MONTH_SHORT[month],
      fullMonth: month,
      value: data[month]?.Total ?? 0,
    }));
  }, [data]);

  const total = useMemo(
    () => series.reduce((acc, point) => acc + point.value, 0),
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
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-muted-foreground">12-month consumption</span>
        <span className="font-medium tabular-nums">
          {total.toLocaleString()} {unit}
        </span>
      </div>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={series}
            margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="water-area" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor="var(--color-field)"
                  stopOpacity={0.35}
                />
                <stop
                  offset="100%"
                  stopColor="var(--color-field)"
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--color-border)"
              vertical={false}
            />
            <XAxis
              dataKey="month"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }}
              tickMargin={8}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }}
              width={56}
              label={{
                value: `Water consumption (${unit})`,
                angle: -90,
                position: "insideLeft",
                offset: 10,
                style: {
                  textAnchor: "middle",
                  fill: "var(--color-muted-foreground)",
                  fontSize: 11,
                },
              }}
            />
            <Tooltip
              cursor={{
                stroke: "var(--color-field)",
                strokeWidth: 1,
                strokeDasharray: "3 3",
              }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const point = payload[0]?.payload as ChartPoint | undefined;
                if (!point) return null;
                return (
                  <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-md">
                    <div className="font-medium text-foreground">
                      {point.fullMonth}
                    </div>
                    <div className="text-muted-foreground">
                      <span className="tabular-nums text-foreground">
                        {point.value.toLocaleString()}
                      </span>{" "}
                      {unit}
                    </div>
                  </div>
                );
              }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="var(--color-field)"
              strokeWidth={2.5}
              fill="url(#water-area)"
              dot={{
                r: 3,
                fill: "var(--color-field)",
                stroke: "var(--color-bone)",
                strokeWidth: 1.5,
              }}
              activeDot={{
                r: 5,
                fill: "var(--color-pulse)",
                stroke: "var(--color-bone)",
                strokeWidth: 2,
              }}
              isAnimationActive
              animationDuration={600}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}