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

function makeUserFields<TValues extends CreateUserValues | UpdateUserValues>(
  mode: "create" | "edit",
): EntityFormField<TValues>[] {
  return [
    {
      name: "username" as never,
      label: "Username",
      autoComplete: "username",
      disabled: mode === "edit",
    },
    {
      name: "email" as never,
      label: "Email",
      type: "email",
      autoComplete: "email",
    },
    { name: "phone_number" as never, label: "Phone number", autoComplete: "tel" },
    { name: "first_name" as never, label: "First name", autoComplete: "given-name" },
    { name: "last_name" as never, label: "Last name", autoComplete: "family-name" },
    {
      name: "text_password" as never,
      label:
        mode === "create"
          ? "Password"
          : "New password (leave blank to keep)",
      type: "password",
      autoComplete: "new-password",
    },
    {
      name: "role" as never,
      label: "Role",
      type: "select",
      options: roleOptions,
    },
    {
      name: "farm_name" as never,
      label: "Farm",
      type: "fk",
      resource: "farms",
      valueKey: "farm_name",
      labelKey: "farm_name",
      placeholder: "Select a farm",
    },
    { name: "is_active" as never, label: "Active", type: "boolean" },
  ];
}

const createFields = makeUserFields<CreateUserValues>("create");
const editFields = makeUserFields<UpdateUserValues>("edit");

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