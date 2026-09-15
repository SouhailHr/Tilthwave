import { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface DashboardStatCardProps {
  label: string;
  value: number | string;
  hint?: ReactNode;
  icon?: LucideIcon;
  isPending?: boolean;
  tone?: "default" | "pulse" | "harvest" | "loam";
}

const toneClasses: Record<NonNullable<DashboardStatCardProps["tone"]>, string> =
  {
    default: "text-foreground",
    pulse: "text-field",
    harvest: "text-harvest",
    loam: "text-loam",
  };

export function DashboardStatCard({
  label,
  value,
  hint,
  icon: Icon,
  isPending = false,
  tone = "default",
}: DashboardStatCardProps) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-3">
        <div className="grid gap-1">
          <span className="text-xs uppercase tracking-wide text-muted-foreground">
            {label}
          </span>
          {isPending ? (
            <Skeleton className="h-8 w-20" />
          ) : (
            <span
              className={cn(
                "font-heading text-3xl font-semibold leading-none",
                toneClasses[tone],
              )}
            >
              {value}
            </span>
          )}
          {hint ? (
            <span className="text-xs text-muted-foreground">{hint}</span>
          ) : null}
        </div>
        {Icon ? <Icon className="size-5 text-muted-foreground" /> : null}
      </CardContent>
    </Card>
  );
}