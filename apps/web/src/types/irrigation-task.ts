export const IRRIGATION_TASK_STATUSES = [
  "pending",
  "in progress",
  "completed",
  "canceled",
] as const;
export type IrrigationTaskStatus = (typeof IRRIGATION_TASK_STATUSES)[number];

export interface IrrigationTask {
  id: number;
  zone_name: string;
  status: IrrigationTaskStatus;
  /** Minutes the task ran; set when it completes. */
  duration?: number | null;
  created_date?: string;
  updated_date?: string;
  performed_by?: string;
}

export interface CreateIrrigationTaskInput {
  zone_name: string;
  status: IrrigationTaskStatus;
}

export type UpdateIrrigationTaskInput = Partial<CreateIrrigationTaskInput> & { duration?: number | null };