import type { DeviceStatus } from "@/types/water-source";

export interface WaterSwitcher {
  id: number;
  water_source_serial_number: string;
  sensor_serial_number: string | null;
  status: DeviceStatus;
  zone_name: string;
  serial_number: string;
  created_date?: string;
  updated_date?: string;
  performed_by?: string;
}

export interface CreateWaterSwitcherInput {
  water_source_serial_number: string;
  sensor_serial_number?: string | null;
  status: DeviceStatus;
  zone_name: string;
  serial_number: string;
}

export type UpdateWaterSwitcherInput = Partial<CreateWaterSwitcherInput>;