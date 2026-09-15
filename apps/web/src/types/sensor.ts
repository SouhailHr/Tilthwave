export const SENSOR_TYPES = [
  "switcher_sensor",
  "source_sensor",
  "temperature_sensor",
  "moisture_sensor",
  "saturation_sensor",
] as const;
export type SensorType = (typeof SENSOR_TYPES)[number];

export interface Sensor {
  id: number;
  type: SensorType;
  is_active: boolean | null;
  serial_number: string;
  assigned_to_type: string | null;
  zone_name: string | null;
  water_switcher: string | null;
  water_source: string | null;
  created_date?: string;
  updated_date?: string;
  performed_by?: string;
}

export interface CreateSensorInput {
  type: SensorType;
  is_active?: boolean | null;
  serial_number: string;
  assigned_to_type?: string | null;
  zone_name?: string | null;
  water_switcher?: string | null;
  water_source?: string | null;
}

export type UpdateSensorInput = Partial<CreateSensorInput>;