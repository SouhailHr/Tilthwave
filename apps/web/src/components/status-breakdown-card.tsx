import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type BreakdownTone = "field" | "pulse" | "harvest" | "loam" | "muted";

const toneClasses: Record<BreakdownTone, { bar: string; dot: string }> = {
  field: { bar: "bg-furrow", dot: "bg-furrow" },
  pulse: { bar: "bg-shoot", dot: "bg-shoot" },
  harvest: { bar: "bg-amber", dot: "bg-amber" },
  loam: { bar: "bg-loam", dot: "bg-loam" },
  muted: { bar: "bg-muted-foreground/30", dot: "bg-muted-foreground/40" },
};

export interface BreakdownEntry {
  label: string;
  value: number;
  tone: BreakdownTone;
}

interface StatusBreakdownCardProps {
  title: string;
  href?: string;
  entries: BreakdownEntry[];
  total: number;
  isPending?: boolean;
}

export function StatusBreakdownCard({
  title,
  href,
  entries,
  total,
  isPending = false,
}: StatusBreakdownCardProps) {
  return (
    <Card>
      <CardContent className="grid gap-3">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-wide text-muted-foreground">
            {title}
          </span>
          {href ? (
            <Link
              href={href}
              className="flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              View
              <ArrowRight className="size-3" />
            </Link>
          ) : null}
        </div>
        {isPending ? (
          <>
            <Skeleton className="h-7 w-16" />
            <Skeleton className="h-2 w-full" />
            <Skeleton className="h-3 w-3/4" />
          </>
        ) : (
          <>
            <span className="font-heading text-2xl font-semibold leading-none">
              {total}
            </span>
            {total > 0 ? (
              <div className="flex h-2 overflow-hidden rounded-full bg-muted">
                {entries.map((entry) =>
                  entry.value > 0 ? (
                    <div
                      key={entry.label}
                      className={cn("h-full", toneClasses[entry.tone].bar)}
                      style={{ width: `${(entry.value / total) * 100}%` }}
                      title={`${entry.label}: ${entry.value}`}
                    />
                  ) : null,
                )}
              </div>
            ) : (
              <div className="h-2 rounded-full bg-muted" />
            )}
            <ul className="grid gap-1 text-xs">
              {entries.map((entry) => (
                <li
                  key={entry.label}
                  className="flex items-center justify-between gap-2"
                >
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <span
                      className={cn(
                        "inline-block size-2 rounded-full",
                        toneClasses[entry.tone].dot,
                      )}
                    />
                    {entry.label}
                  </span>
                  <span className="font-medium tabular-nums text-foreground">
                    {entry.value}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  );
}