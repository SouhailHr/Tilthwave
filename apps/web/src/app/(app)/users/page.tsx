"use client";

import { z } from "zod";

import { useCreateUser, useUpdateUser } from "@/api/users";
import { EntityCrudPage } from "@/components/entity-crud-page";
import type { EntityFormField } from "@/components/entity-form";
import type { Column } from "@/components/entity-table";
import { Badge } from "@/components/ui/badge";
import { passwordSchema } from "@/lib/password-schema";
import {
  USER_ROLES,
  type CreateUserInput,
  type UpdateUserInput,
  type User,
  type UserRole,
} from "@/types/user";

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
  // 8 matches the API (it 422s on less); the form used to say 6 and let those through to fail.
  text_password: passwordSchema,
});

// No password here: a user changes their own in Settings, and a forgotten one goes through the
// reset link on the sign-in page. An admin no longer types someone else's password into a form.
// Nor a farm: the API ignores farm_name on PATCH (a user cannot be moved between farms), so
// offering the select would show a success toast and change nothing.
const updateUserSchema = z.object({
  ...baseUserShape,
  username: z.string(),
}).omit({ farm_name: true });

type CreateUserValues = z.infer<typeof createUserSchema>;
type UpdateUserValues = z.infer<typeof updateUserSchema>;

// The shared fields are typed against the intersection of both value shapes: react-hook-form's
// Path<T> can't be computed for a still-generic T constrained to a union, which is what once
// forced a cast on every single field. Against the concrete intersection the compiler verifies
// each name normally, and each list asserts once at assembly instead of once per field.
type CommonUserValues = CreateUserValues & UpdateUserValues;

const contactFields: EntityFormField<CommonUserValues>[] = [
  { name: "email", label: "Email", type: "email", autoComplete: "email" },
  { name: "phone_number", label: "Phone number", autoComplete: "tel" },
  { name: "first_name", label: "First name", autoComplete: "given-name" },
  { name: "last_name", label: "Last name", autoComplete: "family-name" },
];

const roleField: EntityFormField<CommonUserValues> = {
  name: "role",
  label: "Role",
  type: "select",
  options: roleOptions,
};
const activeField: EntityFormField<CommonUserValues> = { name: "is_active", label: "Active", type: "boolean" };
const farmField: EntityFormField<CreateUserValues> = {
  name: "farm_name",
  label: "Farm",
  type: "fk",
  resource: "farms",
  valueKey: "farm_name",
  labelKey: "farm_name",
  placeholder: "Select a farm",
};

const createFields: EntityFormField<CreateUserValues>[] = [
  { name: "username", label: "Username", autoComplete: "username" },
  ...(contactFields as EntityFormField<CreateUserValues>[]),
  {
    name: "text_password",
    label: "Password",
    type: "password",
    autoComplete: "new-password",
    description: "At least 8 characters. They can change it later from Settings.",
  },
  roleField as EntityFormField<CreateUserValues>,
  farmField,
  activeField as EntityFormField<CreateUserValues>,
];

const editFields: EntityFormField<UpdateUserValues>[] = [
  { name: "username", label: "Username", autoComplete: "username", disabled: true },
  ...(contactFields as EntityFormField<UpdateUserValues>[]),
  roleField as EntityFormField<UpdateUserValues>,
  activeField as EntityFormField<UpdateUserValues>,
];

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
  };
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
        role: user.role,
        is_active: user.is_active,
      })}
      toCreateInput={toCreateInput}
      toUpdateInput={toUpdateInput}
      useCreate={useCreateUser}
      useUpdate={useUpdateUser}
    />
  );
}