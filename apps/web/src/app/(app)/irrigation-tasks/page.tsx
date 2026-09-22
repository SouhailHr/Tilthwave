"use client";

import { z } from "zod";

import {
  useCreateIrrigationTask,
  useUpdateIrrigationTask,
} from "@/api/irrigation-tasks";
import {
  IRRIGATION_TASK_STATUSES,
  type CreateIrrigationTaskInput,
  type IrrigationTask,
  type IrrigationTaskStatus,
  type UpdateIrrigationTaskInput,
} from "@/types/irrigation-task";
import { Badge } from "@/components/ui/badge";
import { formatDateTime } from "@/utils/dates";
import { EntityCrudPage } from "@/components/entity-crud-page";
import type { EntityFormField } from "@/components/entity-form";
import type { Column } from "@/components/entity-table";

const irrigationTaskSchema = z.object({
  zone_name: z.string().min(1, "Zone is required"),
  status: z.enum(IRRIGATION_TASK_STATUSES),
});

type IrrigationTaskValues = z.infer<typeof irrigationTaskSchema>;

const statusOptions: { value: IrrigationTaskStatus; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "in progress", label: "In progress" },
  { value: "completed", label: "Completed" },
  { value: "canceled", label: "Canceled" },
];

const irrigationTaskFields: EntityFormField<IrrigationTaskValues>[] = [
  {
    name: "zone_name",
    label: "Zone",
    type: "fk",
    resource: "zones",
    valueKey: "zone_name",
    labelKey: "zone_name",
    placeholder: "Select a zone",
  },
  { name: "status", label: "Status", type: "select", options: statusOptions },
];

const statusVariant: Record<
  IrrigationTaskStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  pending: "secondary",
  "in progress": "default",
  completed: "outline",
  canceled: "destructive",
};

const irrigationTaskColumns: Column<IrrigationTask>[] = [
  {
    key: "id",
    header: "Task",
    cell: (task) => <span className="font-medium">#{task.id}</span>,
  },
  { key: "zone_name", header: "Zone", cell: (task) => task.zone_name },
  {
    key: "status",
    header: "Status",
    cell: (task) => (
      <Badge variant={statusVariant[task.status]} className="capitalize">
        {task.status}
      </Badge>
    ),
  },
  {
    key: "created_date",
    header: "Created",
    cell: (task) => (
      <span className="tabular-nums text-muted-foreground">{formatDateTime(task.created_date)}</span>
    ),
  },
];

export default function IrrigationTasksPage() {
  return (
    <EntityCrudPage<
      IrrigationTask,
      IrrigationTaskValues,
      IrrigationTaskValues,
      CreateIrrigationTaskInput,
      UpdateIrrigationTaskInput
    >
      resource="irrigation-tasks"
      title="Irrigation tasks"
      description="Scheduled and active irrigation jobs."
      entity="task"
      columns={irrigationTaskColumns}
      createSchema={irrigationTaskSchema}
      createFields={irrigationTaskFields}
      createDefaults={{ zone_name: "", status: "pending" }}
      toEditDefaults={(task) => ({
        zone_name: task.zone_name,
        status: task.status,
      })}
      toCreateInput={(values) => values}
      toUpdateInput={(values) => values}
      useCreate={useCreateIrrigationTask}
      useUpdate={useUpdateIrrigationTask}
    />
  );
}