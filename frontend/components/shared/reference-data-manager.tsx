"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2, Pencil, Trash2, Download } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"
import { DataTable } from "@/components/shared/data-table"
import {
  BulkUploadDialog,
  type BulkUploadColumn,
  type BulkUploadResult,
} from "@/components/shared/bulk-upload-dialog"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { apiClient } from "@/lib/api/client"
import { truncate } from "@/lib/utils"
import { exportToXlsx } from "@/lib/xlsx-export"

export type RefDataField = {
  name: string
  label: string
  type?: "input" | "textarea"
  placeholder?: string
  maxLength?: number
  optional?: boolean
}

export type RefDataColumn = {
  key: string
  header: string
  truncateAt?: number
}

export type RefDataBulkUpload = {
  /** POST endpoint accepting `{ items: [...] }`. */
  importPath: string
  entityLabelPlural: string
  /** Spreadsheet contract — keys must match the API item fields. */
  columns: BulkUploadColumn[]
  sampleRows: (string | number)[][]
  templateFileName: string
  notes?: string[]
}

export interface ReferenceDataManagerProps {
  title: string
  description: string
  queryKey: readonly unknown[]
  listPath: string
  createPath: string
  updatePath: (id: string) => string
  entityLabel: string
  permission: string
  fields: RefDataField[]
  columns: RefDataColumn[]
  /** Enables the Bulk Upload dialog when the entity has an import endpoint. */
  bulkUpload?: RefDataBulkUpload
  /** Base name for the downloaded records file; defaults to a slug of the title. */
  exportFileName?: string
}

type RefDataRecord = {
  id: string
  is_active: boolean
  [key: string]: unknown
}

type FormValues = Record<string, string>

function buildSchema(fields: RefDataField[]) {
  const shape: Record<string, z.ZodTypeAny> = {}
  for (const field of fields) {
    let value: z.ZodString = z.string()
    if (field.maxLength) {
      value = value.max(field.maxLength, `Max ${field.maxLength} characters`)
    }
    shape[field.name] = field.optional ? value.optional() : value.min(1, `${field.label} is required`)
  }
  return z.object(shape)
}

function defaultValues(fields: RefDataField[], record?: RefDataRecord | null): FormValues {
  return Object.fromEntries(
    fields.map((field) => [field.name, record ? String(record[field.name] ?? "") : ""])
  )
}

export function ReferenceDataManager({
  title,
  description,
  queryKey,
  listPath,
  createPath,
  updatePath,
  entityLabel,
  permission,
  fields,
  columns,
  bulkUpload,
  exportFileName,
}: ReferenceDataManagerProps) {
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<RefDataRecord | null>(null)
  const [deactivating, setDeactivating] = useState<RefDataRecord | null>(null)
  const qc = useQueryClient()

  const schema = buildSchema(fields)

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: async () => {
      const { data } = await apiClient.GET(listPath as never)
      return ((data as unknown) as { items?: RefDataRecord[] })?.items ?? ((data as unknown) as RefDataRecord[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema as never) as never })

  function openCreateDialog() {
    setEditing(null)
    reset(defaultValues(fields))
    setOpen(true)
  }

  function openEditDialog(record: RefDataRecord) {
    setEditing(record)
    reset(defaultValues(fields, record))
    setOpen(true)
  }

  const saveMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      if (editing) {
        await apiClient.PATCH(updatePath(editing.id) as never, { body: values } as never)
      } else {
        await apiClient.POST(createPath as never, { body: values } as never)
      }
    },
    onSuccess: () => {
      toast.success(editing ? `${entityLabel} updated` : `${entityLabel} created`)
      qc.invalidateQueries({ queryKey })
      setOpen(false)
      setEditing(null)
    },
    onError: () =>
      toast.error(editing ? `Failed to update ${entityLabel.toLowerCase()}` : `Failed to create ${entityLabel.toLowerCase()}`),
  })

  const deactivateMutation = useMutation({
    mutationFn: async (record: RefDataRecord) => {
      await apiClient.PATCH(updatePath(record.id) as never, { body: { is_active: false } } as never)
    },
    onSuccess: () => {
      toast.success(`${entityLabel} deactivated`)
      qc.invalidateQueries({ queryKey })
      setDeactivating(null)
    },
    onError: () => toast.error(`Failed to deactivate ${entityLabel.toLowerCase()}`),
  })

  const tableColumns: ColumnDef<RefDataRecord>[] = [
    {
      id: "si_no",
      header: "SI No",
      cell: ({ row }) => row.index + 1,
    },
    ...columns.map<ColumnDef<RefDataRecord>>((col) => ({
      id: col.key,
      header: col.header,
      cell: ({ row }) => {
        const value = row.original[col.key]
        const text = value == null ? "" : String(value)
        if (!text) return <span className="text-muted-foreground">—</span>
        if (col.truncateAt) {
          return <span title={text}>{truncate(text, col.truncateAt)}</span>
        }
        return <span className="block max-w-[80ch] whitespace-normal break-words">{text}</span>
      },
    })),
    {
      id: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.is_active ? "ACTIVE" : "INACTIVE"} />,
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <PermissionGate permission={permission}>
          <div className="flex items-center justify-end gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation()
                openEditDialog(row.original)
              }}
            >
              <Pencil className="size-4" />
            </Button>
            {row.original.is_active && (
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation()
                  setDeactivating(row.original)
                }}
              >
                <Trash2 className="size-4 text-destructive" />
              </Button>
            )}
          </div>
        </PermissionGate>
      ),
    },
  ]

  const records = data ?? []

  async function handleDownload() {
    const slug = exportFileName ?? title.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "")
    await exportToXlsx({
      fileName: `${slug}.xlsx`,
      sheetName: entityLabel.slice(0, 31),
      columns: [
        ...columns.map((col) => ({ key: col.key, header: col.key })),
        { key: "status", header: "status", value: (r: RefDataRecord) => (r.is_active ? "ACTIVE" : "INACTIVE") },
      ],
      rows: records,
    })
  }

  return (
    <div>
      <PageHeader
        title={title}
        description={description}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" onClick={handleDownload} disabled={records.length === 0}>
              <Download />
              Download
            </Button>
            {bulkUpload && (
              <PermissionGate permission={permission}>
                <BulkUploadDialog
                  entityLabel={entityLabel}
                  entityLabelPlural={bulkUpload.entityLabelPlural}
                  columns={bulkUpload.columns}
                  sampleRows={bulkUpload.sampleRows}
                  templateFileName={bulkUpload.templateFileName}
                  notes={bulkUpload.notes}
                  onImported={() => qc.invalidateQueries({ queryKey })}
                  onImport={async (rows) => {
                    const items = rows.map((row) =>
                      Object.fromEntries(
                        bulkUpload.columns.map((col) => [col.key, String(row[col.key] ?? "").trim()])
                      )
                    )
                    const { data } = await apiClient.POST(bulkUpload.importPath as never, {
                      body: { items },
                    } as never)
                    return (data as unknown) as BulkUploadResult
                  }}
                />
              </PermissionGate>
            )}
            <PermissionGate permission={permission}>
              <Button onClick={openCreateDialog}>
                <Plus />
                New {entityLabel}
              </Button>
            </PermissionGate>
          </div>
        }
      />

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? `Edit ${entityLabel}` : `Create ${entityLabel}`}</DialogTitle>
          </DialogHeader>
          <form
            id="ref-data-form"
            onSubmit={handleSubmit((v) => saveMutation.mutate(v))}
            className="space-y-4 py-2"
          >
            {fields.map((field) => (
              <div className="space-y-2" key={field.name}>
                <Label htmlFor={`ref-${field.name}`}>{field.label}</Label>
                {field.type === "textarea" ? (
                  <Textarea
                    id={`ref-${field.name}`}
                    rows={3}
                    placeholder={field.placeholder}
                    {...register(field.name)}
                  />
                ) : (
                  <Input
                    id={`ref-${field.name}`}
                    placeholder={field.placeholder}
                    {...register(field.name)}
                  />
                )}
                {errors[field.name] && (
                  <p className="text-sm text-destructive">{errors[field.name]?.message as string}</p>
                )}
              </div>
            ))}
          </form>
          <DialogFooter showCloseButton>
            <Button type="submit" form="ref-data-form" disabled={isSubmitting || saveMutation.isPending}>
              {(isSubmitting || saveMutation.isPending) && <Loader2 className="animate-spin" />}
              {editing ? "Save Changes" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deactivating != null}
        onOpenChange={(v) => !v && setDeactivating(null)}
        title={`Deactivate ${entityLabel}`}
        description={`This will mark this ${entityLabel.toLowerCase()} as inactive. It can be reactivated later by editing it. Continue?`}
        confirmLabel="Deactivate"
        variant="destructive"
        loading={deactivateMutation.isPending}
        onConfirm={() => deactivating && deactivateMutation.mutate(deactivating)}
      />

      <DataTable
        columns={tableColumns}
        data={records}
        loading={isLoading}
        emptyMessage={`No ${entityLabel.toLowerCase()}s found.`}
      />
    </div>
  )
}
