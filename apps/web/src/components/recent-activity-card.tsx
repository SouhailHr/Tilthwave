import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { irrigationTaskStatusVariant } from "@/lib/status-ui";
import type { IrrigationTask, } from "@/types/irrigation-task";
import { formatRelative } from "@/utils/dates";


interface RecentActivityCardProps {
  tasks: IrrigationTask[];
  isPending: boolean;
}

export function RecentActivityCard({
  tasks,
  isPending,
}: RecentActivityCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle>Recent irrigation activity</CardTitle>
        <Link
          href="/irrigation-tasks"
          className="flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          View all
          <ArrowRight className="size-3" />
        </Link>
      </CardHeader>
      <CardContent>
        {isPending ? (
          <div className="grid gap-2">
            {Array.from({ length: 4 }).map((_, idx) => (
              <Skeleton key={idx} className="h-10 w-full" />
            ))}
          </div>
        ) : tasks.length === 0 ? (
          <p className="text-sm text-muted-foreground">No activity yet.</p>
        ) : (
          <ul className="grid divide-y divide-border">
            {tasks.map((task) => (
              <li
                key={task.id}
                className="flex items-center justify-between gap-3 py-2 first:pt-0 last:pb-0"
              >
                <div className="grid">
                  <span className="text-sm font-medium">{task.zone_name}</span>
                  <span className="text-xs text-muted-foreground">
                    Task #{task.id} · {formatRelative(task.updated_date ?? task.created_date)}
                  </span>
                </div>
                <Badge
                  variant={irrigationTaskStatusVariant[task.status]}
                  className="capitalize"
                >
                  {task.status}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}