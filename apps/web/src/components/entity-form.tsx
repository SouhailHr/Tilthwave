"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ReactNode, useState } from "react";
import { DefaultValues, FieldValues, Path, useForm, type ControllerRenderProps, type Resolver } from "react-hook-form";
import type { ZodType } from "zod";

import { useEntityList } from "@/api/entity-queries";
import { toApiError } from "@/api/errors";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useDebounced } from "@/hooks/useDebounced";
import { cn } from "@/lib/utils";
import type { EntityWithId } from "@/types/pagination";
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyZod = ZodType<any, any>;

type SelectOption = { value: string; label: string };

type CommonField<TValues extends FieldValues> = {
  name: Path<TValues>;
  label: string;
  description?: string;
  disabled?: boolean;
  placeholder?: string;
};

type TextLikeField<TValues extends FieldValues> = CommonField<TValues> & {
  type?: "text" | "email" | "password" | "number" | "date" | "datetime-local";
  autoComplete?: string;
};

type SelectField<TValues extends FieldValues> = CommonField<TValues> & {
  type: "select";
  options: SelectOption[];
};

type BooleanField<TValues extends FieldValues> = CommonField<TValues> & {
  type: "boolean";
};

type TextareaField<TValues extends FieldValues> = CommonField<TValues> & {
  type: "textarea";
  rows?: number;
};

type FKField<TValues extends FieldValues> = CommonField<TValues> & {
  type: "fk";
  resource: string;
  valueKey: string;
  labelKey: string;
};

export type EntityFormField<TValues extends FieldValues> =
  | TextLikeField<TValues>
  | SelectField<TValues>
  | BooleanField<TValues>
  | TextareaField<TValues>
  | FKField<TValues>;

const FK_PAGE_SIZE = 100;

interface EntityFormProps<TValues extends FieldValues> {
  schema: ZodType<TValues>;
  fields: EntityFormField<TValues>[];
  defaultValues: DefaultValues<TValues>;
  onSubmit: (values: TValues) => Promise<void> | void;
  onCancel?: () => void;
  submitLabel?: string;
  pendingLabel?: string;
  footerSlot?: ReactNode;
}

export function EntityForm<TValues extends FieldValues>({
  schema,
  fields,
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Save",
  pendingLabel = "Saving…",
  footerSlot,
}: EntityFormProps<TValues>) {
  const form = useForm<TValues>({
    resolver: zodResolver(schema as AnyZod) as unknown as Resolver<TValues>,
    defaultValues,
  });

  const isSubmitting = form.formState.isSubmitting;

  // The API's validation errors land on the fields they name. The caller has already reported
  // the failure (toast); what it rethrows is only for this mapping, so nothing propagates.
  const submit = async (values: TValues) => {
    try {
      await onSubmit(values);
    } catch (err) {
      const { fieldErrors } = toApiError(err);
      for (const [name, messages] of Object.entries(fieldErrors ?? {})) {
        if (name in values) {
          form.setError(name as Path<TValues>, { type: "server", message: messages.join(" ") });
        }
      }
    }
  };

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(submit)}
        className="grid gap-4"
        noValidate
      >
        {fields.map((field) => (
          <FormField
            key={field.name as string}
            control={form.control}
            name={field.name}
            render={({ field: rhfField }) => (
              <FormItem>
                {field.type !== "boolean" ? (
                  <FormLabel>{field.label}</FormLabel>
                ) : null}
                <FormControl>
                  <FieldRenderer field={field} rhfField={rhfField} />
                </FormControl>
                {field.description ? (
                  <FormDescription>{field.description}</FormDescription>
                ) : null}
                <FormMessage />
              </FormItem>
            )}
          />
        ))}

        {footerSlot}

        <div className="flex justify-end gap-2">
          {onCancel ? (
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
          ) : null}
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? pendingLabel : submitLabel}
          </Button>
        </div>
      </form>
    </Form>
  );
}

type RHFField = ControllerRenderProps<FieldValues, string>;

function FieldRenderer<TValues extends FieldValues>({
  field,
  rhfField,
}: {
  field: EntityFormField<TValues>;
  rhfField: RHFField;
}) {
  if (field.type === "select") {
    return (
      <Select
        value={(rhfField.value as string | undefined) ?? ""}
        onValueChange={(next) => rhfField.onChange(next ?? "")}
        disabled={field.disabled}
      >
        <SelectTrigger className="w-full">
          <SelectValue placeholder={field.placeholder} />
        </SelectTrigger>
        <SelectContent>
          {field.options.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  }

  if (field.type === "fk") {
    return (
      <FkSelect
        resource={field.resource}
        valueKey={field.valueKey}
        labelKey={field.labelKey}
        placeholder={field.placeholder}
        disabled={field.disabled}
        value={(rhfField.value as string | undefined) ?? ""}
        onValueChange={(next) => rhfField.onChange(next ?? "")}
      />
    );
  }

  if (field.type === "boolean") {
    const checked = rhfField.value === true || rhfField.value === "true";
    return (
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={checked}
          disabled={field.disabled}
          onChange={(e) => rhfField.onChange(e.target.checked)}
          className="size-4 rounded border-input"
        />
        <span>{field.label}</span>
      </label>
    );
  }

  if (field.type === "textarea") {
    return (
      <textarea
        rows={field.rows ?? 3}
        placeholder={field.placeholder}
        disabled={field.disabled}
        value={
          rhfField.value === undefined || rhfField.value === null
            ? ""
            : String(rhfField.value)
        }
        onChange={(e) => rhfField.onChange(e.target.value)}
        className={cn(
          "flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm",
          "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
        )}
      />
    );
  }

  // text-like fallback (text/email/password/number/date/datetime-local)
  const isNumber = field.type === "number";
  return (
    <Input
      type={field.type ?? "text"}
      placeholder={field.placeholder}
      autoComplete={field.autoComplete}
      disabled={field.disabled}
      {...rhfField}
      value={
        rhfField.value === undefined || rhfField.value === null
          ? ""
          : (rhfField.value as string | number)
      }
      onChange={(e) => {
        if (isNumber) {
          const v = e.target.value;
          rhfField.onChange(v === "" ? "" : Number(v));
        } else {
          rhfField.onChange(e.target.value);
        }
      }}
    />
  );
}

function FkSelect({
  resource,
  valueKey,
  labelKey,
  value,
  onValueChange,
  placeholder,
  disabled,
}: {
  resource: string;
  valueKey: string;
  labelKey: string;
  value: string;
  onValueChange: (next: string) => void;
  placeholder?: string;
  disabled?: boolean;
}) {
  // One page of options. When the resource has more rows than a page, a filter box appears and
  // narrows the list server-side (the API's `search` matches the resource's identifier), so a
  // farm with 500 sensors is not silently cut to the first 100.
  const [filterInput, setFilterInput] = useState("");
  const filter = useDebounced(filterInput);
  const { data, isPending, isError } = useEntityList<EntityWithId & Record<string, unknown>>(resource, {
    size: FK_PAGE_SIZE,
    ...(filter ? { search: filter } : {}),
  });

  const options: SelectOption[] = (data?.items ?? []).map((item) => ({
    value: String(item[valueKey] ?? ""),
    label: String(item[labelKey] ?? item[valueKey] ?? ""),
  }));
  const total = data?.total ?? 0;
  const overflow = total > options.length;

  return (
    <div className="grid gap-1.5">
      {overflow || filter !== "" ? (
        <Input
          type="search"
          value={filterInput}
          disabled={disabled}
          placeholder={`Type to narrow ${total} ${resource.replace("-", " ")}`}
          aria-label={`Filter ${resource}`}
          onChange={(e) => setFilterInput(e.target.value)}
        />
      ) : null}
      <Select
        value={value}
        onValueChange={(next) => onValueChange(next ?? "")}
        disabled={disabled || isPending}
      >
        <SelectTrigger className="w-full">
          <SelectValue
            placeholder={isPending ? "Loading…" : isError ? "Failed to load" : (placeholder ?? "Select…")}
          />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {overflow ? (
        <p className="text-xs text-muted-foreground">
          Showing the first {options.length} of {total}; type above to find the rest.
        </p>
      ) : null}
    </div>
  );
}
