import type { VariantProps } from "class-variance-authority";

import { badgeVariants } from "@/components/ui/badge";
import type { IrrigationTaskStatus } from "@/types/irrigation-task";
import type { DeviceStatus } from "@/types/water-source";

/**
 * How a status is offered in a form and drawn in a table: one place per status vocabulary, so a
 * water source, a water switcher, the irrigation-tasks page and the dashboard's activity card
 * cannot drift apart.
 */
export type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>["variant"]>;

export const DEVICE_STATUS_OPTIONS: { value: DeviceStatus; label: string }[] = [
  { value: "On", label: "On" },
  { value: "Off", label: "Off" },
  { value: "Error", label: "Error" },
];

export const deviceStatusVariant: Record<DeviceStatus, BadgeVariant> = {
  On: "default",
  Off: "secondary",
  Error: "destructive",
};

export const IRRIGATION_TASK_STATUS_OPTIONS: { value: IrrigationTaskStatus; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "in progress", label: "In progress" },
  { value: "completed", label: "Completed" },
  { value: "canceled", label: "Canceled" },
];

export const irrigationTaskStatusVariant: Record<IrrigationTaskStatus, BadgeVariant> = {
  pending: "secondary",
  "in progress": "default",
  completed: "outline",
  canceled: "destructive",
};
