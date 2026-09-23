"use client";

import { z } from "zod";

import { useCreateSensor, useUpdateSensor } from "@/api/sensors";
import { EntityCrudPage } from "@/components/entity-crud-page";
import type { EntityFormField } from "@/components/entity-form";
import type { Column } from "@/components/entity-table";
import { Badge } from "@/components/ui/badge";
import {
  SENSOR_TYPES,
  type CreateSensorInput,
  type Sensor,
  type SensorType,
  type UpdateSensorInput,
} from "@/types/sensor";

// What a sensor of each type attaches to. This is the API's own rule (only the three zone types
// can be linked to a zone; a switcher/source sensor is linked through the water switcher/source
// row), so the form derives the target from the type instead of asking for it separately. It
// also fixes two things the old form got wrong: it never sent `assigned_to_type`, so an edit
// that picked a water source was answered 200 and silently dropped; and it rendered the
// assignment from request-only fields a row never carries, so the column was always empty.
type Target = "zone" | "water_switcher" | "water_source";
type TargetField = "zone_name" | "water_switcher" | "water_source";

const TARGET_FOR_TYPE: Record<SensorType, Target> = {
  switcher_sensor: "water_switcher",
  source_sensor: "water_source",
  temperature_sensor: "zone",
  moisture_sensor: "zone",
  saturation_sensor: "zone",
};
const TARGET_LABEL: Record<Target, string> = {
  zone: "Zone",
  water_switcher: "Water switcher",
  water_source: "Water source",
};
const TARGET_FIELD: Record<Target, TargetField> = {
  zone: "zone_name",
  water_switcher: "water_switcher",
  water_source: "water_source",
};

const sensorTypeLabel: Record<SensorType, string> = {
  switcher_sensor: "Switcher",
  source_sensor: "Source",
  temperature_sensor: "Temperature",
  moisture_sensor: "Moisture",
  saturation_sensor: "Saturation",
};

const sensorTypeOptions: { value: SensorType; label: string }[] = [
  { value: "switcher_sensor", label: "Switcher sensor" },
  { value: "source_sensor", label: "Source sensor" },
  { value: "temperature_sensor", label: "Temperature sensor" },
  { value: "moisture_sensor", label: "Moisture sensor" },
  { value: "saturation_sensor", label: "Saturation sensor" },
];

const sensorShape = z.object({
  serial_number: z.string().min(1, "Serial number is required"),
  type: z.enum(SENSOR_TYPES),
  is_active: z.boolean(),
  zone_name: z.string(),
  water_switcher: z.string(),
  water_source: z.string(),
});
type SensorValues = z.infer<typeof sensorShape>;

function targetOf(values: SensorValues): { target: Target; value: string } {
  const target = TARGET_FOR_TYPE[values.type];
  return { target, value: values[TARGET_FIELD[target]] };
}

// Creating a sensor creates its link in the same request, so the target for its type is required.
const createSensorSchema = sensorShape.superRefine((values, ctx) => {
  const { target, value } = targetOf(values);
  if (!value) {
    ctx.addIssue({
      code: "custom",
      path: [TARGET_FIELD[target]],
      message: `A ${sensorTypeLabel[values.type].toLowerCase()} sensor must be assigned to a ${TARGET_LABEL[target].toLowerCase()}`,
    });
  }
});
// Editing: leaving the target empty keeps the current assignment.
const editSensorSchema = sensorShape;

const sensorFields: EntityFormField<SensorValues>[] = [
  { name: "serial_number", label: "Serial number", placeholder: "e.g. SENTEMP00123" },
  {
    name: "type",
    label: "Type",
    type: "select",
    options: sensorTypeOptions,
    description:
      "Decides where it goes: moisture, saturation and temperature sensors on a zone; a switcher sensor on a water switcher; a source sensor on a water source.",
  },
  { name: "is_active", label: "Active", type: "boolean" },
  {
    name: "zone_name",
    label: "Zone",
    type: "fk",
    resource: "zones",
    valueKey: "zone_name",
    labelKey: "zone_name",
    placeholder: "Select a zone",
    description: "For moisture, saturation and temperature sensors.",
  },
  {
    name: "water_switcher",
    label: "Water switcher",
    type: "fk",
    resource: "water-switchers",
    valueKey: "serial_number",
    labelKey: "serial_number",
    placeholder: "Select a switcher",
    description: "For switcher sensors.",
  },
  {
    name: "water_source",
    label: "Water source",
    type: "fk",
    resource: "water-sources",
    valueKey: "serial_number",
    labelKey: "serial_number",
    placeholder: "Select a source",
    description: "For source sensors.",
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
    key: "assigned_to",
    header: "Assigned to",
    cell: (sensor) =>
      sensor.assigned_to ? (
        <span>
          <span className="text-muted-foreground">
            {TARGET_LABEL[TARGET_FOR_TYPE[sensor.type]]} ·{" "}
          </span>
          {sensor.assigned_to}
        </span>
      ) : (
        <span className="text-muted-foreground">Unassigned</span>
      ),
  },
];

function toCreateInput(values: SensorValues): CreateSensorInput {
  const { target, value } = targetOf(values);
  return {
    serial_number: values.serial_number,
    type: values.type,
    is_active: values.is_active,
    assigned_to_type: target,
    zone_name: target === "zone" ? value : null,
    water_switcher: target === "water_switcher" ? value : null,
    water_source: target === "water_source" ? value : null,
  };
}

function toUpdateInput(values: SensorValues): UpdateSensorInput {
  const { target, value } = targetOf(values);
  const base: UpdateSensorInput = {
    serial_number: values.serial_number,
    type: values.type,
    is_active: values.is_active,
  };
  if (!value) return base; // no target chosen: keep the current assignment
  return {
    ...base,
    assigned_to_type: target,
    zone_name: target === "zone" ? value : null,
    water_switcher: target === "water_switcher" ? value : null,
    water_source: target === "water_source" ? value : null,
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
      createSchema={createSensorSchema}
      editSchema={editSensorSchema}
      createFields={sensorFields}
      editFields={sensorFields}
      createDefaults={{
        serial_number: "",
        type: "moisture_sensor",
        is_active: true,
        zone_name: "",
        water_switcher: "",
        water_source: "",
      }}
      toEditDefaults={(sensor) => {
        // Prefill the current assignment in the slot for this sensor's type.
        const target = TARGET_FOR_TYPE[sensor.type];
        const current = sensor.assigned_to ?? "";
        return {
          serial_number: sensor.serial_number,
          type: sensor.type,
          is_active: !!sensor.is_active,
          zone_name: target === "zone" ? current : "",
          water_switcher: target === "water_switcher" ? current : "",
          water_source: target === "water_source" ? current : "",
        };
      }}
      toCreateInput={toCreateInput}
      toUpdateInput={toUpdateInput}
      useCreate={useCreateSensor}
      useUpdate={useUpdateSensor}
    />
  );
}
