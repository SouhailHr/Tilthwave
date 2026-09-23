"use client";

import { z } from "zod";


import { useCreateFarm, useUpdateFarm } from "@/api/farms";
import { EntityCrudPage } from "@/components/entity-crud-page";
import type { EntityFormField } from "@/components/entity-form";
import type { Column } from "@/components/entity-table";
import { positiveNumber } from "@/lib/form-fields";
import type { CreateFarmInput, Farm, UpdateFarmInput } from "@/types/farm";

const farmSchema = z.object({
  farm_name: z.string().min(1, "Farm name is required").max(100),
  address: z.string().min(1, "Address is required").max(255),
  size: positiveNumber("Size"),
  lat: z
    .string()
    .refine(
      (v) => v === "" || !Number.isNaN(Number(v)),
      "Latitude must be a number",
    ),
  lon: z
    .string()
    .refine(
      (v) => v === "" || !Number.isNaN(Number(v)),
      "Longitude must be a number",
    ),
});

type FarmValues = z.infer<typeof farmSchema>;

const farmFields: EntityFormField<FarmValues>[] = [
  { name: "farm_name", label: "Farm name", placeholder: "e.g. Sunny Farms" },
  { name: "address", label: "Address" },
  {
    name: "size", type: "number",
    label: "Size (hectares)",
    placeholder: "e.g. 120",
    description: "Total cultivated area.",
  },
  {
    name: "lat",
    label: "Latitude",
    placeholder: "e.g. 36.8065",
    description: "Optional. Provide both latitude and longitude or neither.",
  },
  { name: "lon", label: "Longitude", placeholder: "e.g. 10.1815" },
];

const farmColumns: Column<Farm>[] = [
  {
    key: "farm_name",
    header: "Name",
    cell: (farm) => <span className="font-medium">{farm.farm_name}</span>,
  },
  { key: "address", header: "Address", cell: (farm) => farm.address },
  { key: "size", header: "Size", cell: (farm) => `${farm.size} ha` },
  {
    key: "location",
    header: "Location",
    cell: (farm) =>
      farm.location
        ? `${farm.location.lat.toFixed(4)}, ${farm.location.lon.toFixed(4)}`
        : "—",
  },
];

function buildInput(values: FarmValues): CreateFarmInput {
  const hasLat = values.lat !== "";
  const hasLon = values.lon !== "";
  return {
    farm_name: values.farm_name,
    address: values.address,
    size: values.size,
    location:
      hasLat && hasLon
        ? { lat: Number(values.lat), lon: Number(values.lon) }
        : null,
  };
}

export default function FarmsPage() {
  return (
    <EntityCrudPage<Farm, FarmValues, FarmValues, CreateFarmInput, UpdateFarmInput>
      resource="farms"
      title="Farms"
      description="Manage farms and their boundaries."
      entity="farm"
      columns={farmColumns}
      createSchema={farmSchema}
      createFields={farmFields}
      createDefaults={{
        farm_name: "",
        address: "",
        lat: "",
        lon: "",
      }}
      toEditDefaults={(farm) => ({
        farm_name: farm.farm_name,
        address: farm.address,
        size: farm.size,
        lat: farm.location ? String(farm.location.lat) : "",
        lon: farm.location ? String(farm.location.lon) : "",
      })}
      toCreateInput={buildInput}
      toUpdateInput={buildInput}
      useCreate={useCreateFarm}
      useUpdate={useUpdateFarm}
    />
  );
}