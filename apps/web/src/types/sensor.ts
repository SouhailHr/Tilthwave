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
  /**
   * What the sensor is attached to, as the list endpoint reports it: a zone name, or a water
   * switcher / water source serial, depending on the sensor's type. Null when unassigned.
   */
  assigned_to?: string | null;
  // Request-only: what the create/update forms send to make or change the link. The API strips
  // them before persisting, so a row read back never carries them.
  assigned_to_type?: string | null;
  zone_name?: string | null;
  water_switcher?: string | null;
  water_source?: string | null;
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