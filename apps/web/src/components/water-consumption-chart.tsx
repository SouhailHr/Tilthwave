"use client";

import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui/skeleton";

export const WaterConsumptionChart = dynamic(
  () =>
    import("./water-consumption-chart-impl").then((m) => m.WaterConsumptionChart),
  {
    ssr: false,
    loading: () => <Skeleton className="h-72 w-full" />,
  },
);