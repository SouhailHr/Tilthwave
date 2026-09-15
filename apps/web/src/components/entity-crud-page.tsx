"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import type { DefaultValues, FieldValues } from "react-hook-form";
import type { UseMutationResult } from "@tanstack/react-query";
import type { ZodType } from "zod";

import { toApiError, type ApiError } from "@/api/errors";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EntityForm, type EntityFormField } from "@/components/entity-form";
import { type Column, EntityTable } from "@/components/entity-table";
import { useDisclosure } from "@/hooks/useDisclosure";
import type { EntityWithId } from "@/types/pagination";

type UpdateArgs<TUpdate> = { id: number | string; input: TUpdate };
type Mode = "create" | "edit";

interface EntityCrudPageProps<
  T extends EntityWithId,
  CreateValues extends FieldValues,
  EditValues extends FieldValues,
  TCreate,
  TUpdate,
> {
  resource: string;
  title: string;
  description?: string;
  /** singular noun, lowercase ("zone", "water source") */
  entity: string;
  columns: Column<T>[];
  createSchema: ZodType<CreateValues>;
  editSchema?: ZodType<EditValues>;
  createFields: EntityFormField<CreateValues>[];
  editFields?: EntityFormField<EditValues>[];
  createDefaults: DefaultValues<CreateValues>;
  toEditDefaults: (row: T) => DefaultValues<EditValues>;
  toCreateInput: (values: CreateValues) => TCreate;
  toUpdateInput: (values: EditValues) => TUpdate;
  useCreate: () => UseMutationResult<T, ApiError, TCreate>;
  useUpdate: () => UseMutationResult<T, ApiError, UpdateArgs<TUpdate>>;
  canEdit?: (row: T) => boolean;
  canDelete?: (row: T) => boolean;
}

export function EntityCrudPage<
  T extends EntityWithId,
  CreateValues extends FieldValues,
  EditValues extends FieldValues,
  TCreate,
  TUpdate,
>(props: EntityCrudPageProps<T, CreateValues, EditValues, TCreate, TUpdate>) {
  const {
    resource,
    title,
    description,
    entity,
    columns,
    createSchema,
    editSchema,
    createFields,
    editFields,
    createDefaults,
    toEditDefaults,
    toCreateInput,
    toUpdateInput,
    useCreate,
    useUpdate,
    canEdit,
    canDelete,
  } = props;

  const dialog = useDisclosure();
  const [editing, setEditing] = useState<T | null>(null);

  const createMutation = useCreate();
  const updateMutation = useUpdate();

  const openCreate = useCallback(() => {
    setEditing(null);
    dialog.open();
  }, [dialog]);

  const openEdit = useCallback(
    (row: T) => {
      setEditing(row);
      dialog.open();
    },
    [dialog],
  );

  const handleClose = useCallback(() => {
    dialog.close();
    setEditing(null);
  }, [dialog]);

  const capitalised = `${entity[0].toUpperCase()}${entity.slice(1)}`;

  const reportError = useCallback(
    (err: unknown, mode: Mode) => {
      const apiError = toApiError(
        err,
        `Failed to ${mode === "create" ? "create" : "update"} ${entity}`,
      );
      toast.error(apiError.message, {
        description: apiError.requestId
          ? `ref: ${apiError.requestId}`
          : undefined,
      });
    },
    [entity],
  );

  const submitCreate = useCallback(
    async (values: CreateValues) => {
      try {
        await createMutation.mutateAsync(toCreateInput(values));
        toast.success(`${capitalised} created`);
        handleClose();
      } catch (err) {
        reportError(err, "create");
      }
    },
    [createMutation, toCreateInput, capitalised, handleClose, reportError],
  );

  const submitUpdate = useCallback(
    async (values: EditValues) => {
      if (!editing) return;
      try {
        await updateMutation.mutateAsync({
          id: editing.id,
          input: toUpdateInput(values),
        });
        toast.success(`${capitalised} updated`);
        handleClose();
      } catch (err) {
        reportError(err, "edit");
      }
    },
    [editing, updateMutation, toUpdateInput, capitalised, handleClose, reportError],
  );

  const isEditing = editing !== null;
  const resolvedEditSchema = (editSchema ?? createSchema) as ZodType<EditValues>;
  const resolvedEditFields = (editFields ??
    (createFields as unknown as EntityFormField<EditValues>[]));

  return (
    <>
      <EntityTable<T>
        resource={resource}
        title={title}
        description={description}
        columns={columns}
        onCreate={openCreate}
        onEdit={openEdit}
        canEdit={canEdit}
        canDelete={canDelete}
      />

      <Dialog
        open={dialog.isOpen}
        onOpenChange={(open) => {
          if (!open) handleClose();
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {isEditing ? `Edit ${entity}` : `New ${entity}`}
            </DialogTitle>
            <DialogDescription>
              {isEditing
                ? `Update ${entity} details.`
                : `Add a new ${entity}.`}
            </DialogDescription>
          </DialogHeader>

          {isEditing ? (
            <EntityForm<EditValues>
              schema={resolvedEditSchema}
              fields={resolvedEditFields}
              defaultValues={toEditDefaults(editing)}
              onSubmit={submitUpdate}
              onCancel={handleClose}
              submitLabel="Save"
              pendingLabel="Saving…"
            />
          ) : (
            <EntityForm<CreateValues>
              schema={createSchema}
              fields={createFields}
              defaultValues={createDefaults}
              onSubmit={submitCreate}
              onCancel={handleClose}
              submitLabel="Create"
              pendingLabel="Creating…"
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}