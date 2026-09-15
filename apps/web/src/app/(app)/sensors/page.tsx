"use client";

import { z } from "zod";

import { useCreateSensor, useUpdateSensor } from "@/api/sensors";
import {
  SENSOR_TYPES,
  type CreateSensorInput,
  type Sensor,
  type SensorType,
  type UpdateSensorInput,
} from "@/types/sensor";
import { Badge } from "@/components/ui/badge";
import { EntityCrudPage } from "@/components/entity-crud-page";
import type { EntityFormField } from "@/components/entity-form";
import type { Column } from "@/components/entity-table";

const sensorSchema = z.object({
  serial_number: z.string().min(1, "Serial number is required"),
  type: z.enum(SENSOR_TYPES),
  is_active: z.boolean(),
  zone_name: z.string(),
  water_switcher: z.string(),
  water_source: z.string(),
});

type SensorValues = z.infer<typeof sensorSchema>;

const sensorTypeOptions: { value: SensorType; label: string }[] = [
  { value: "switcher_sensor", label: "Switcher sensor" },
  { value: "source_sensor", label: "Source sensor" },
  { value: "temperature_sensor", label: "Temperature sensor" },
  { value: "moisture_sensor", label: "Moisture sensor" },
  { value: "saturation_sensor", label: "Saturation sensor" },
];

const sensorTypeLabel: Record<SensorType, string> = {
  switcher_sensor: "Switcher",
  source_sensor: "Source",
  temperature_sensor: "Temperature",
  moisture_sensor: "Moisture",
  saturation_sensor: "Saturation",
};

const sensorFields: EntityFormField<SensorValues>[] = [
  { name: "serial_number", label: "Serial number", placeholder: "e.g. SENTEMP00123" },
  { name: "type", label: "Type", type: "select", options: sensorTypeOptions },
  { name: "is_active", label: "Active", type: "boolean" },
  {
    name: "zone_name",
    label: "Zone (optional)",
    type: "fk",
    resource: "zones",
    valueKey: "zone_name",
    labelKey: "zone_name",
    placeholder: "Select a zone",
  },
  {
    name: "water_switcher",
    label: "Water switcher (optional)",
    type: "fk",
    resource: "water-switchers",
    valueKey: "serial_number",
    labelKey: "serial_number",
    placeholder: "Serial",
  },
  {
    name: "water_source",
    label: "Water source (optional)",
    type: "fk",
    resource: "water-sources",
    valueKey: "serial_number",
    labelKey: "serial_number",
    placeholder: "Serial",
  },
];

const sensorColumns: Column<Sensor>[] = [
  {
    key: "serial_number",
    header: "Serial",
    cell: (sensor) => <span className="font-medium">{sensor.serial_number}</span>,
  },
  {
    key: "type",
    header: "Type",
    cell: (sensor) => (
      <Badge variant="secondary">{sensorTypeLabel[sensor.type]}</Badge>
    ),
  },
  {
    key: "is_active",
    header: "Status",
    cell: (sensor) => (
      <Badge variant={sensor.is_active ? "default" : "outline"}>
        {sensor.is_active ? "Active" : "Inactive"}
      </Badge>
    ),
  },
  {
    key: "assignment",
    header: "Assigned to",
    cell: (sensor) =>
      sensor.zone_name ?? sensor.water_switcher ?? sensor.water_source ?? "—",
  },
];

function buildInput(values: SensorValues): CreateSensorInput {
  return {
    serial_number: values.serial_number,
    type: values.type,
    is_active: values.is_active,
    zone_name: values.zone_name || null,
    water_switcher: values.water_switcher || null,
    water_source: values.water_source || null,
  };
}

export default function SensorsPage() {
  return (
    <EntityCrudPage<
      Sensor,
      SensorValues,
      SensorValues,
      CreateSensorInput,
      UpdateSensorInput
    >
      resource="sensors"
      title="Sensors"
      description="Hardware sensors and their assignments."
      entity="sensor"
      columns={sensorColumns}
      createSchema={sensorSchema}
      createFields={sensorFields}
      createDefaults={{
        serial_number: "",
        type: "moisture_sensor",
        is_active: true,
        zone_name: "",
        water_switcher: "",
        water_source: "",
      }}
      toEditDefaults={(sensor) => ({
        serial_number: sensor.serial_number,
        type: sensor.type,
        is_active: !!sensor.is_active,
        zone_name: sensor.zone_name ?? "",
        water_switcher: sensor.water_switcher ?? "",
        water_source: sensor.water_source ?? "",
      })}
      toCreateInput={buildInput}
      toUpdateInput={buildInput}
      useCreate={useCreateSensor}
      useUpdate={useUpdateSensor}
    />
  );
}