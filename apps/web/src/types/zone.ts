import type { FarmLocation } from "@/types/farm";

export interface Zone {
  id: number;
  farm_name: string;
  zone_name: string;
  size: number;
  location: FarmLocation | null;
  soil_type: string;
  moisture_trigger_start: number;
  moisture_trigger_stop: number;
  saturation_trigger_start: number;
  saturation_trigger_stop: number;
  created_date?: string;
  updated_date?: string;
  performed_by?: string;
}

export interface CreateZoneInput {
  farm_name: string;
  zone_name: string;
  size: number;
  location?: FarmLocation | null;
  soil_type: string;
  moisture_trigger_start: number;
  moisture_trigger_stop: number;
  saturation_trigger_start: number;
  saturation_trigger_stop: number;
}

export type UpdateZoneInput = Partial<CreateZoneInput>;