"use client";

import { ReactNode, useCallback, useMemo, useState } from "react";
import { MoreHorizontal, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { useDeleteEntity, useEntityList } from "@/api/_entity";
import { toApiError } from "@/api/errors";
import { useDebounced } from "@/hooks/useDebounced";
import type { EntityWithId } from "@/types/pagination";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export type Column<T> = {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
};

type EntityTableProps<T extends EntityWithId> = {
  resource: string;
  columns: Column<T>[];
  title: string;
  description?: string;
  pageSize?: number;
  searchable?: boolean;
  onCreate?: () => void;
  onEdit?: (row: T) => void;
  canDelete?: (row: T) => boolean;
  canEdit?: (row: T) => boolean;
  emptyMessage?: string;
};

export function EntityTable<T extends EntityWithId>({
  resource,
  columns,
  title,
  description,
  pageSize = 20,
  searchable = true,
  onCreate,
  onEdit,
  canDelete,
  canEdit,
  emptyMessage = "No records yet.",
}: EntityTableProps<T>) {
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const search = useDebounced(searchInput);
  const [confirmRow, setConfirmRow] = useState<T | null>(null);

  // Back to page 1 when the debounced search value changes (not on every keystroke): a search
  // narrows the result set, so the page the user was on may no longer exist. Done during render,
  // the way React adjusts state when a value changes, rather than in an effect one render late.
  const [searchOfPage, setSearchOfPage] = useState(search);
  if (search !== searchOfPage) {
    setSearchOfPage(search);
    setPage(1);
  }

  const params = useMemo(() => {
    return { page, size: pageSize, ...(search ? { search } : {}) };
  }, [page, pageSize, search]);

  const { data, isPending, isError, error } = useEntityList<T>(resource, params);
  const deleteMutation = useDeleteEntity(resource);

  const handleConfirmDelete = useCallback(async () => {
    if (!confirmRow) return;
    try {
      await deleteMutation.mutateAsync(confirmRow.id);
      toast.success("Deleted");
      setConfirmRow(null);
    } catch (err) {
      const apiError = toApiError(err, "Failed to delete");
      toast.error(apiError.message, {
        description: apiError.requestId ? `ref: ${apiError.requestId}` : undefined,
      });
    }
  }, [confirmRow, deleteMutation]);

  const items = data?.items ?? [];
  const totalPages = data?.pages ?? 1;

  return (
    <div className="grid gap-4">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold">{title}</h1>
          {description ? (
            <p className="text-sm text-muted-foreground">{description}</p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {searchable ? (
            <div className="relative">
              <Search className="absolute top-1/2 left-2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search…"
                className="pl-8"
              />
            </div>
          ) : null}
          {onCreate ? (
            <Button onClick={onCreate} data-icon="inline-start">
              <Plus />
              New
            </Button>
          ) : null}
        </div>
      </header>

      {isError ? (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load"}
        </div>
      ) : null}

      {/* Desktop table */}
      <div className="hidden rounded-xl border bg-card md:block">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col) => (
                <TableHead key={col.key} className={col.className}>
                  {col.header}
                </TableHead>
              ))}
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isPending ? (
              Array.from({ length: 5 }).map((_, idx) => (
                <TableRow key={`skeleton-${idx}`}>
                  {columns.map((col) => (
                    <TableCell key={col.key}>
                      <Skeleton className="h-4 w-3/4" />
                    </TableCell>
                  ))}
                  <TableCell />
                </TableRow>
              ))
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length + 1}
                  className="text-center text-muted-foreground"
                >
                  {emptyMessage}
                </TableCell>
              </TableRow>
            ) : (
              items.map((row) => (
                <TableRow key={row.id}>
                  {columns.map((col) => (
                    <TableCell key={col.key} className={col.className}>
                      {col.cell(row)}
                    </TableCell>
                  ))}
                  <TableCell>
                    <RowActions
                      row={row}
                      onEdit={onEdit}
                      canEdit={canEdit}
                      canDelete={canDelete}
                      onRequestDelete={setConfirmRow}
                    />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Mobile cards */}
      <div className="grid gap-2 md:hidden">
        {isPending ? (
          Array.from({ length: 4 }).map((_, idx) => (
            <Skeleton key={`m-skel-${idx}`} className="h-24 w-full rounded-xl" />
          ))
        ) : items.length === 0 ? (
          <div className="rounded-xl border bg-card p-6 text-center text-sm text-muted-foreground">
            {emptyMessage}
          </div>
        ) : (
          items.map((row) => (
            <div
              key={row.id}
              className="flex items-start justify-between gap-3 rounded-xl border bg-card p-3"
            >
              <dl className="grid flex-1 gap-1 text-sm">
                {columns.map((col) => (
                  <div key={col.key} className="flex justify-between gap-3">
                    <dt className="text-muted-foreground">{col.header}</dt>
                    <dd className="text-right">{col.cell(row)}</dd>
                  </div>
                ))}
              </dl>
              <RowActions
                row={row}
                onEdit={onEdit}
                canEdit={canEdit}
                canDelete={canDelete}
                onRequestDelete={setConfirmRow}
              />
            </div>
          ))
        )}
      </div>

      {totalPages > 1 ? (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Page {data?.page ?? page} of {totalPages} · {data?.total ?? 0} total
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}

      <Dialog
        open={confirmRow !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmRow(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete record?</DialogTitle>
            <DialogDescription>
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmRow(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting…" : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

type RowActionsProps<T extends EntityWithId> = {
  row: T;
  onEdit?: (row: T) => void;
  onRequestDelete: (row: T) => void;
  canEdit?: (row: T) => boolean;
  canDelete?: (row: T) => boolean;
};

function RowActions<T extends EntityWithId>({
  row,
  onEdit,
  onRequestDelete,
  canEdit,
  canDelete,
}: RowActionsProps<T>) {
  const editAllowed = onEdit && (canEdit ? canEdit(row) : true);
  const deleteAllowed = canDelete ? canDelete(row) : true;
  if (!editAllowed && !deleteAllowed) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" size="icon-sm" aria-label="Row actions">
            <MoreHorizontal />
          </Button>
        }
      />
      <DropdownMenuContent align="end">
        {editAllowed ? (
          <DropdownMenuItem onClick={() => onEdit?.(row)}>
            <Pencil />
            Edit
          </DropdownMenuItem>
        ) : null}
        {deleteAllowed ? (
          <DropdownMenuItem
            variant="destructive"
            onClick={() => onRequestDelete(row)}
          >
            <Trash2 />
            Delete
          </DropdownMenuItem>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}