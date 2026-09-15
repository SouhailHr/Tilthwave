"use client";

import { z } from "zod";

import { useCreateWaterSource, useUpdateWaterSource } from "@/api/water-sources";
import {
  DEVICE_STATUSES,
  type CreateWaterSourceInput,
  type DeviceStatus,
  type UpdateWaterSourceInput,
  type WaterSource,
} from "@/types/water-source";
import { Badge } from "@/components/ui/badge";
import { EntityCrudPage } from "@/components/entity-crud-page";
import type { EntityFormField } from "@/components/entity-form";
import type { Column } from "@/components/entity-table";

const positiveNumber = (label: string) =>
  z
    .string()
    .refine((v) => v !== "" && !Number.isNaN(Number(v)), `${label} is required`)
    .refine((v) => Number(v) > 0, `${label} must be greater than 0`);

const waterSourceSchema = z.object({
  serial_number: z.string().min(1, "Serial number is required"),
  farm_name: z.string().min(1, "Farm is required"),
  type: z.string().min(1, "Type is required").max(50),
  water_pressure: positiveNumber("Water pressure"),
  water_volume: positiveNumber("Water volume"),
  status: z.enum(DEVICE_STATUSES),
  sensor_serial_number: z.string(),
});

type WaterSourceValues = z.infer<typeof waterSourceSchema>;

const statusOptions: { value: DeviceStatus; label: string }[] = [
  { value: "On", label: "On" },
  { value: "Off", label: "Off" },
  { value: "Error", label: "Error" },
];

const waterSourceFields: EntityFormField<WaterSourceValues>[] = [
  { name: "serial_number", label: "Serial number", placeholder: "e.g. WSDEEP00123" },
  {
    name: "farm_name",
    label: "Farm",
    type: "fk",
    resource: "farms",
    valueKey: "farm_name",
    labelKey: "farm_name",
    placeholder: "Select a farm",
  },
  { name: "type", label: "Type", placeholder: "e.g. deep groundwater" },
  { name: "water_pressure", label: "Water pressure", placeholder: "e.g. 15.5" },
  { name: "water_volume", label: "Water volume (L)", placeholder: "e.g. 1000" },
  { name: "status", label: "Status", type: "select", options: statusOptions },
  {
    name: "sensor_serial_number",
    label: "Sensor (optional)",
    type: "fk",
    resource: "sensors",
    valueKey: "serial_number",
    labelKey: "serial_number",
    placeholder: "Sensor serial",
  },
];

const statusVariant: Record<DeviceStatus, "default" | "secondary" | "destructive"> = {
  On: "default",
  Off: "secondary",
  Error: "destructive",
};

const waterSourceColumns: Column<WaterSource>[] = [
  {
    key: "serial_number",
    header: "Serial",
    cell: (ws) => <span className="font-medium">{ws.serial_number}</span>,
  },
  { key: "farm_name", header: "Farm", cell: (ws) => ws.farm_name },
  { key: "type", header: "Type", cell: (ws) => ws.type },
  {
    key: "metrics",
    header: "Pressure / Volume",
    cell: (ws) => `${ws.water_pressure} / ${ws.water_volume}`,
  },
  {
    key: "status",
    header: "Status",
    cell: (ws) => <Badge variant={statusVariant[ws.status]}>{ws.status}</Badge>,
  },
];

function buildInput(values: WaterSourceValues): CreateWaterSourceInput {
  return {
    serial_number: values.serial_number,
    farm_name: values.farm_name,
    type: values.type,
    water_pressure: Number(values.water_pressure),
    water_volume: Number(values.water_volume),
    status: values.status,
    sensor_serial_number: values.sensor_serial_number || null,
  };
}

export default function WaterSourcesPage() {
  return (
    <EntityCrudPage<
      WaterSource,
      WaterSourceValues,
      WaterSourceValues,
      CreateWaterSourceInput,
      UpdateWaterSourceInput
    >
      resource="water-sources"
      title="Water sources"
      description="Wells, reservoirs, and other water inputs."
      entity="water source"
      columns={waterSourceColumns}
      createSchema={waterSourceSchema}
      createFields={waterSourceFields}
      createDefaults={{
        serial_number: "",
        farm_name: "",
        type: "",
        water_pressure: "",
        water_volume: "",
        status: "On",
        sensor_serial_number: "",
      }}
      toEditDefaults={(ws) => ({
        serial_number: ws.serial_number,
        farm_name: ws.farm_name,
        type: ws.type,
        water_pressure: String(ws.water_pressure),
        water_volume: String(ws.water_volume),
        status: ws.status,
        sensor_serial_number: ws.sensor_serial_number ?? "",
      })}
      toCreateInput={buildInput}
      toUpdateInput={buildInput}
      useCreate={useCreateWaterSource}
      useUpdate={useUpdateWaterSource}
    />
  );
}