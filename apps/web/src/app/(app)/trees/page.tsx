"use client";

import { z } from "zod";

import { useCreateTree, useUpdateTree } from "@/api/trees";
import { EntityCrudPage } from "@/components/entity-crud-page";
import type { EntityFormField } from "@/components/entity-form";
import type { Column } from "@/components/entity-table";
import type { CreateTreeInput, Tree, UpdateTreeInput } from "@/types/tree";


const treeSchema = z.object({
  zone_name: z.string().min(1, "Zone is required"),
  variety: z.string().min(1, "Variety is required"),
  planting_date: z.string().min(1, "Planting date is required"),
  height: z.number({ error: "Height is required" }).positive("Height must be greater than 0"),
  width_diameter: z.number({ error: "Width diameter is required" }).positive("Width diameter must be greater than 0"),
  trunk_diameter: z.number({ error: "Trunk diameter is required" }).positive("Trunk diameter must be greater than 0"),
  serial_number: z.string().min(1, "Serial number is required"),
});

type TreeValues = z.infer<typeof treeSchema>;

const treeFields: EntityFormField<TreeValues>[] = [
  { name: "serial_number", label: "Serial number", placeholder: "e.g. OLIVE00123" },
  {
    name: "zone_name",
    label: "Zone",
    type: "fk",
    resource: "zones",
    valueKey: "zone_name",
    labelKey: "zone_name",
    placeholder: "Select a zone",
  },
  { name: "variety", label: "Variety", placeholder: "e.g. Olive" },
  { name: "planting_date", label: "Planting date", type: "date" },
  { name: "height", type: "number", label: "Height (m)", placeholder: "e.g. 5.5" },
  { name: "width_diameter", type: "number", label: "Width diameter (m)", placeholder: "e.g. 2" },
  { name: "trunk_diameter", type: "number", label: "Trunk diameter (m)", placeholder: "e.g. 0.3" },
];

const treeColumns: Column<Tree>[] = [
  {
    key: "serial_number",
    header: "Serial",
    cell: (tree) => <span className="font-medium">{tree.serial_number}</span>,
  },
  { key: "variety", header: "Variety", cell: (tree) => tree.variety },
  { key: "zone_name", header: "Zone", cell: (tree) => tree.zone_name },
  { key: "planting_date", header: "Planted", cell: (tree) => tree.planting_date },
  {
    key: "size",
    header: "H × W × T (m)",
    cell: (tree) =>
      `${tree.height} × ${tree.width_diameter} × ${tree.trunk_diameter}`,
  },
];

function buildInput(values: TreeValues): CreateTreeInput {
  return {
    zone_name: values.zone_name,
    variety: values.variety,
    planting_date: values.planting_date,
    height: values.height,
    width_diameter: values.width_diameter,
    trunk_diameter: values.trunk_diameter,
    serial_number: values.serial_number,
  };
}

export default function TreesPage() {
  return (
    <EntityCrudPage<Tree, TreeValues, TreeValues, CreateTreeInput, UpdateTreeInput>
      resource="trees"
      title="Trees"
      description="Individual trees with their planting details."
      entity="tree"
      columns={treeColumns}
      createSchema={treeSchema}
      createFields={treeFields}
      createDefaults={{
        serial_number: "",
        zone_name: "",
        variety: "",
        planting_date: "",
      }}
      toEditDefaults={(tree) => ({
        serial_number: tree.serial_number,
        zone_name: tree.zone_name,
        variety: tree.variety,
        planting_date: tree.planting_date,
        height: tree.height,
        width_diameter: tree.width_diameter,
        trunk_diameter: tree.trunk_diameter,
      })}
      toCreateInput={buildInput}
      toUpdateInput={buildInput}
      useCreate={useCreateTree}
      useUpdate={useUpdateTree}
    />
  );
}