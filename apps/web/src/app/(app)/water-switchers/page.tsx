"use client";

import { z } from "zod";

import {
  useCreateWaterSwitcher,
  useUpdateWaterSwitcher,
} from "@/api/water-switchers";
import { EntityCrudPage } from "@/components/entity-crud-page";
import type { EntityFormField } from "@/components/entity-form";
import type { Column } from "@/components/entity-table";
import { Badge } from "@/components/ui/badge";
import { DEVICE_STATUS_OPTIONS, deviceStatusVariant } from "@/lib/status-ui";
import { DEVICE_STATUSES } from "@/types/water-source";
import type {
  CreateWaterSwitcherInput,
  UpdateWaterSwitcherInput,
  WaterSwitcher,
} from "@/types/water-switcher";

const waterSwitcherSchema = z.object({
  serial_number: z.string().min(1, "Serial number is required"),
  water_source_serial_number: z.string().min(1, "Water source is required"),
  zone_name: z.string().min(1, "Zone is required").max(100),
  status: z.enum(DEVICE_STATUSES),
  sensor_serial_number: z.string(),
});

type WaterSwitcherValues = z.infer<typeof waterSwitcherSchema>;

const waterSwitcherFields: EntityFormField<WaterSwitcherValues>[] = [
  { name: "serial_number", label: "Serial number", placeholder: "e.g. WS00123" },
  {
    name: "water_source_serial_number",
    label: "Water source",
    type: "fk",
    resource: "water-sources",
    valueKey: "serial_number",
    labelKey: "serial_number",
    placeholder: "Select a water source",
  },
  {
    name: "zone_name",
    label: "Zone",
    type: "fk",
    resource: "zones",
    valueKey: "zone_name",
    labelKey: "zone_name",
    placeholder: "Select a zone",
  },
  { name: "status", label: "Status", type: "select", options: DEVICE_STATUS_OPTIONS },
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

const waterSwitcherColumns: Column<WaterSwitcher>[] = [
  {
    key: "serial_number",
    header: "Serial",
    cell: (sw) => <span className="font-medium">{sw.serial_number}</span>,
  },
  {
    key: "water_source",
    header: "Source",
    cell: (sw) => sw.water_source_serial_number,
  },
  { key: "zone_name", header: "Zone", cell: (sw) => sw.zone_name },
  {
    key: "status",
    header: "Status",
    cell: (sw) => <Badge variant={deviceStatusVariant[sw.status]}>{sw.status}</Badge>,
  },
];

function buildInput(values: WaterSwitcherValues): CreateWaterSwitcherInput {
  return {
    serial_number: values.serial_number,
    water_source_serial_number: values.water_source_serial_number,
    zone_name: values.zone_name,
    status: values.status,
    sensor_serial_number: values.sensor_serial_number || null,
  };
}

export default function WaterSwitchersPage() {
  return (
    <EntityCrudPage<
      WaterSwitcher,
      WaterSwitcherValues,
      WaterSwitcherValues,
      CreateWaterSwitcherInput,
      UpdateWaterSwitcherInput
    >
      resource="water-switchers"
      title="Water switchers"
      description="Valves connecting water sources to irrigation zones."
      entity="water switcher"
      columns={waterSwitcherColumns}
      createSchema={waterSwitcherSchema}
      createFields={waterSwitcherFields}
      createDefaults={{
        serial_number: "",
        water_source_serial_number: "",
        zone_name: "",
        status: "On",
        sensor_serial_number: "",
      }}
      toEditDefaults={(sw) => ({
        serial_number: sw.serial_number,
        water_source_serial_number: sw.water_source_serial_number,
        zone_name: sw.zone_name,
        status: sw.status,
        sensor_serial_number: sw.sensor_serial_number ?? "",
      })}
      toCreateInput={buildInput}
      toUpdateInput={buildInput}
      useCreate={useCreateWaterSwitcher}
      useUpdate={useUpdateWaterSwitcher}
    />
  );
}