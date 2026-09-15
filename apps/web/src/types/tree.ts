export interface Tree {
  id: number;
  zone_name: string;
  variety: string;
  planting_date: string;
  height: number;
  width_diameter: number;
  trunk_diameter: number;
  serial_number: string;
  created_date?: string;
  updated_date?: string;
  performed_by?: string;
}

export interface CreateTreeInput {
  zone_name: string;
  variety: string;
  planting_date: string;
  height: number;
  width_diameter: number;
  trunk_diameter: number;
  serial_number: string;
}

export type UpdateTreeInput = Partial<CreateTreeInput>;