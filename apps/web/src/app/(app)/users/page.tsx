"use client";

import { z } from "zod";

import { useCreateUser, useUpdateUser } from "@/api/users";
import {
  USER_ROLES,
  type CreateUserInput,
  type UpdateUserInput,
  type User,
  type UserRole,
} from "@/types/user";
import { Badge } from "@/components/ui/badge";
import { EntityCrudPage } from "@/components/entity-crud-page";
import type { EntityFormField } from "@/components/entity-form";
import type { Column } from "@/components/entity-table";

const roleOptions: { value: UserRole; label: string }[] = [
  { value: "admin", label: "Admin" },
  { value: "owner", label: "Owner" },
  { value: "engineer", label: "Engineer" },
  { value: "worker", label: "Worker" },
];

const baseUserShape = {
  email: z.email("Invalid email"),
  phone_number: z.string().min(1, "Phone number is required"),
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
  role: z.enum(USER_ROLES),
  is_active: z.boolean(),
  farm_name: z.string(),
};

const createUserSchema = z.object({
  ...baseUserShape,
  username: z.string().min(1, "Username is required"),
  text_password: z.string().min(6, "Password must be at least 6 characters"),
});

const updateUserSchema = z.object({
  ...baseUserShape,
  username: z.string(),
  text_password: z.string(),
});

type CreateUserValues = z.infer<typeof createUserSchema>;
type UpdateUserValues = z.infer<typeof updateUserSchema>;

// CreateUserValues and UpdateUserValues share every field name below (both spread
// baseUserShape, plus username/text_password with the same names in both schemas) - only
// a couple of validators differ. react-hook-form's Path<T> can't be computed for a still-generic
// T constrained to a union (TypeScript can't distribute a keyof-like check over an
// uninstantiated type parameter), which is what forced a cast on every single field before.
// Building the array against the concrete intersection type instead lets the compiler verify
// each field name normally; each of the two call sites then asserts it once, not once per field.
type CommonUserValues = CreateUserValues & UpdateUserValues;

function makeUserFields(mode: "create" | "edit"): EntityFormField<CommonUserValues>[] {
  return [
    {
      name: "username",
      label: "Username",
      autoComplete: "username",
      disabled: mode === "edit",
    },
    {
      name: "email",
      label: "Email",
      type: "email",
      autoComplete: "email",
    },
    { name: "phone_number", label: "Phone number", autoComplete: "tel" },
    { name: "first_name", label: "First name", autoComplete: "given-name" },
    { name: "last_name", label: "Last name", autoComplete: "family-name" },
    {
      name: "text_password",
      label:
        mode === "create"
          ? "Password"
          : "New password (leave blank to keep)",
      type: "password",
      autoComplete: "new-password",
    },
    {
      name: "role",
      label: "Role",
      type: "select",
      options: roleOptions,
    },
    {
      name: "farm_name",
      label: "Farm",
      type: "fk",
      resource: "farms",
      valueKey: "farm_name",
      labelKey: "farm_name",
      placeholder: "Select a farm",
    },
    { name: "is_active", label: "Active", type: "boolean" },
  ];
}

const createFields = makeUserFields("create") as EntityFormField<CreateUserValues>[];
const editFields = makeUserFields("edit") as EntityFormField<UpdateUserValues>[];

const roleBadgeVariant: Record<UserRole, "default" | "secondary" | "outline"> = {
  admin: "default",
  owner: "default",
  engineer: "secondary",
  worker: "outline",
};

const userColumns: Column<User>[] = [
  {
    key: "username",
    header: "Username",
    cell: (user) => <span className="font-medium">{user.username}</span>,
  },
  { key: "email", header: "Email", cell: (user) => user.email },
  {
    key: "name",
    header: "Name",
    cell: (user) =>
      [user.first_name, user.last_name].filter(Boolean).join(" ") || "—",
  },
  {
    key: "role",
    header: "Role",
    cell: (user) => (
      <Badge variant={roleBadgeVariant[user.role]} className="capitalize">
        {user.role}
      </Badge>
    ),
  },
  { key: "farm_name", header: "Farm", cell: (user) => user.farm_name ?? "—" },
  {
    key: "is_active",
    header: "Status",
    cell: (user) => (
      <Badge variant={user.is_active ? "default" : "outline"}>
        {user.is_active ? "Active" : "Inactive"}
      </Badge>
    ),
  },
];

function toCreateInput(values: CreateUserValues): CreateUserInput {
  return {
    username: values.username,
    email: values.email,
    phone_number: values.phone_number,
    text_password: values.text_password,
    first_name: values.first_name,
    last_name: values.last_name,
    role: values.role,
    is_active: values.is_active,
    farm_name: values.farm_name || null,
  };
}

function toUpdateInput(values: UpdateUserValues): UpdateUserInput {
  const input: UpdateUserInput = {
    email: values.email,
    phone_number: values.phone_number,
    first_name: values.first_name,
    last_name: values.last_name,
    role: values.role,
    is_active: values.is_active,
    farm_name: values.farm_name || null,
  };
  if (values.text_password) input.text_password = values.text_password;
  return input;
}

export default function UsersPage() {
  return (
    <EntityCrudPage<
      User,
      CreateUserValues,
      UpdateUserValues,
      CreateUserInput,
      UpdateUserInput
    >
      resource="users"
      title="Users"
      description="Manage farm operators and their roles."
      entity="user"
      columns={userColumns}
      createSchema={createUserSchema}
      editSchema={updateUserSchema}
      createFields={createFields}
      editFields={editFields}
      createDefaults={{
        username: "",
        email: "",
        phone_number: "",
        first_name: "",
        last_name: "",
        text_password: "",
        role: "worker",
        farm_name: "",
        is_active: true,
      }}
      toEditDefaults={(user) => ({
        username: user.username,
        email: user.email,
        phone_number: user.phone_number,
        first_name: user.first_name,
        last_name: user.last_name,
        text_password: "",
        role: user.role,
        farm_name: user.farm_name ?? "",
        is_active: user.is_active,
      })}
      toCreateInput={toCreateInput}
      toUpdateInput={toUpdateInput}
      useCreate={useCreateUser}
      useUpdate={useUpdateUser}
    />
  );
}