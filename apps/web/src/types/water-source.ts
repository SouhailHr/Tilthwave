export const DEVICE_STATUSES = ["On", "Off", "Error"] as const;
export type DeviceStatus = (typeof DEVICE_STATUSES)[number];

export interface WaterSource {
  id: number;
  farm_name: string;
  sensor_serial_number: string | null;
  type: string;
  water_pressure: number;
  water_volume: number;
  status: DeviceStatus;
  serial_number: string;
  created_date?: string;
  updated_date?: string;
  performed_by?: string;
}

export interface CreateWaterSourceInput {
  farm_name: string;
  sensor_serial_number?: string | null;
  type: string;
  water_pressure: number;
  water_volume: number;
  status: DeviceStatus;
  serial_number: string;
}

export type UpdateWaterSourceInput = Partial<CreateWaterSourceInput>;