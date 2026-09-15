export interface FarmLocation {
  lat: number;
  lon: number;
}

export interface Farm {
  id: number;
  farm_name: string;
  address: string;
  location: FarmLocation | null;
  size: number;
  created_date?: string;
  updated_date?: string;
  performed_by?: string;
}

export interface CreateFarmInput {
  farm_name: string;
  address: string;
  location?: FarmLocation | null;
  size: number;
}

export type UpdateFarmInput = Partial<CreateFarmInput>;

export interface FarmStats {
  total_zones: number;
  total_water_sources: number;
  total_water_switchers: number;
  total_trees: number;
  /** Monthly water consumption keyed by month name (January..December). */
  chart_data: Record<string, { Total: number }>;
}