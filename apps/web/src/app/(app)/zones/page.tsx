"use client";

import { z } from "zod";

import { useCreateZone, useUpdateZone } from "@/api/zones";
import type { CreateZoneInput, UpdateZoneInput, Zone } from "@/types/zone";
import { EntityCrudPage } from "@/components/entity-crud-page";
import type { EntityFormField } from "@/components/entity-form";
import type { Column } from "@/components/entity-table";

const zoneSchema = z.object({
  farm_name: z.string().min(1, "Farm name is required"),
  zone_name: z.string().min(1, "Zone name is required"),
  size: z
    .string()
    .refine((v) => v !== "" && Number.isInteger(Number(v)), "Size must be a whole number")
    .refine((v) => Number(v) > 0, "Size must be greater than 0"),
  soil_type: z.string().min(1, "Soil type is required"),
  moisture_trigger_start: z.string().refine((v) => v !== "", "Required"),
  moisture_trigger_stop: z.string().refine((v) => v !== "", "Required"),
  saturation_trigger_start: z.string().refine((v) => v !== "", "Required"),
  saturation_trigger_stop: z.string().refine((v) => v !== "", "Required"),
  lat: z.string(),
  lon: z.string(),
});

type ZoneValues = z.infer<typeof zoneSchema>;

const zoneFields: EntityFormField<ZoneValues>[] = [
  {
    name: "farm_name",
    label: "Farm",
    type: "fk",
    resource: "farms",
    valueKey: "farm_name",
    labelKey: "farm_name",
    placeholder: "Select a farm",
  },
  { name: "zone_name", label: "Zone name", placeholder: "e.g. Zone 1" },
  { name: "size", label: "Size (m²)", placeholder: "e.g. 1500" },
  { name: "soil_type", label: "Soil type", placeholder: "e.g. Loamy" },
  { name: "moisture_trigger_start", label: "Moisture trigger start" },
  { name: "moisture_trigger_stop", label: "Moisture trigger stop" },
  { name: "saturation_trigger_start", label: "Saturation trigger start" },
  { name: "saturation_trigger_stop", label: "Saturation trigger stop" },
  {
    name: "lat",
    label: "Latitude",
    description: "Optional. Provide both latitude and longitude or neither.",
  },
  { name: "lon", label: "Longitude" },
];

const zoneColumns: Column<Zone>[] = [
  {
    key: "zone_name",
    header: "Zone",
    cell: (zone) => <span className="font-medium">{zone.zone_name}</span>,
  },
  { key: "farm_name", header: "Farm", cell: (zone) => zone.farm_name },
  { key: "size", header: "Size", cell: (zone) => `${zone.size} m²` },
  { key: "soil_type", header: "Soil", cell: (zone) => zone.soil_type },
  {
    key: "triggers",
    header: "Moisture / Saturation",
    cell: (zone) =>
      `${zone.moisture_trigger_start}–${zone.moisture_trigger_stop} / ${zone.saturation_trigger_start}–${zone.saturation_trigger_stop}`,
  },
];

function buildInput(values: ZoneValues): CreateZoneInput {
  const hasLat = values.lat !== "";
  const hasLon = values.lon !== "";
  return {
    farm_name: values.farm_name,
    zone_name: values.zone_name,
    size: Number(values.size),
    soil_type: values.soil_type,
    moisture_trigger_start: Number(values.moisture_trigger_start),
    moisture_trigger_stop: Number(values.moisture_trigger_stop),
    saturation_trigger_start: Number(values.saturation_trigger_start),
    saturation_trigger_stop: Number(values.saturation_trigger_stop),
    location:
      hasLat && hasLon
        ? { lat: Number(values.lat), lon: Number(values.lon) }
        : null,
  };
}

export default function ZonesPage() {
  return (
    <EntityCrudPage<Zone, ZoneValues, ZoneValues, CreateZoneInput, UpdateZoneInput>
      resource="zones"
      title="Zones"
      description="Cultivated areas within a farm."
      entity="zone"
      columns={zoneColumns}
      createSchema={zoneSchema}
      createFields={zoneFields}
      createDefaults={{
        farm_name: "",
        zone_name: "",
        size: "",
        soil_type: "",
        moisture_trigger_start: "50",
        moisture_trigger_stop: "80",
        saturation_trigger_start: "60",
        saturation_trigger_stop: "90",
        lat: "",
        lon: "",
      }}
      toEditDefaults={(zone) => ({
        farm_name: zone.farm_name,
        zone_name: zone.zone_name,
        size: String(zone.size),
        soil_type: zone.soil_type,
        moisture_trigger_start: String(zone.moisture_trigger_start),
        moisture_trigger_stop: String(zone.moisture_trigger_stop),
        saturation_trigger_start: String(zone.saturation_trigger_start),
        saturation_trigger_stop: String(zone.saturation_trigger_stop),
        lat: zone.location ? String(zone.location.lat) : "",
        lon: zone.location ? String(zone.location.lon) : "",
      })}
      toCreateInput={buildInput}
      toUpdateInput={buildInput}
      useCreate={useCreateZone}
      useUpdate={useUpdateZone}
    />
  );
}