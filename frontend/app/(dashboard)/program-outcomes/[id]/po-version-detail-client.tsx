"use client"

import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2, ArrowLeft, Pencil, Trash2 } from "lucide-react"
import { useRouter } from "next/navigation"
import type { ColumnDef } from "@tanstack/react-table"
import { DataTable } from "@/components/shared/data-table"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
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
  DialogTrigger,
} from "@/components/ui/dialog"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { usePermissions } from "@/hooks/use-permission"
import { useAuthStore } from "@/lib/stores/auth-store"

type POVersion = {
  id: string
  name: string
  description: string | null
  is_active: boolean
  po_count: number
}

type ProgramOutcome = {
  id: string
  code: string
  statement: string
  po_version_id?: string | null
  po_type?: string | null
  status: string
}

const createSchema = z.object({
  code: z.string().min(1, "Code is required"),
  po_type: z.string().optional(),
  statement: z.string().min(1, "Statement is required").max(500, "Max 500 characters"),
})

const editSchema = z.object({
  po_type: z.string().optional(),
  statement: z.string().min(1, "Statement is required").max(500, "Max 500 characters"),
})

type CreateFormValues = z.infer<typeof createSchema>
type EditFormValues = z.infer<typeof editSchema>

interface Props {
  versionId: string
}

export function POVersionDetailClient({ versionId }: Props) {
  const [open, setOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<ProgramOutcome | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<ProgramOutcome | null>(null)
  const router = useRouter()
  const qc = useQueryClient()
  const permissions = usePermissions()
  const isInitialized = useAuthStore((state) => state.isInitialized)
  const canManageProgramOutcomes = permissions.some((permission) =>
    ["po.create", "po.update", "po.archive"].includes(permission)
  )

  useEffect(() => {
    if (isInitialized && !canManageProgramOutcomes) {
      router.replace("/overview")
    }
  }, [canManageProgramOutcomes, isInitialized, router])

  const { data: version, isLoading: versionLoading } = useQuery({
    queryKey: queryKeys.poVersions.detail(versionId),
    enabled: isInitialized && canManageProgramOutcomes,
    queryFn: async () => {
      const { data } = await apiClient.GET(`/po-versions/${versionId}` as never)
      return (data as unknown) as POVersion
    },
  })

  const { data: pos = [], isLoading: posLoading } = useQuery({
    queryKey: queryKeys.programOutcomes.byVersion(versionId),
    enabled: isInitialized && canManageProgramOutcomes,
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/program-outcomes?po_version_id=${versionId}` as never
      )
      return ((data as unknown) as ProgramOutcome[]) ?? []
    },
  })

  // ── Create form ──────────────────────────────────────────────────────────

  const createForm = useForm<CreateFormValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { code: `PO${pos.length + 1}`, po_type: "", statement: "" },
  })

  const createMutation = useMutation({
    mutationFn: async (values: CreateFormValues) => {
      await apiClient.POST("/program-outcomes" as never, {
        body: {
          po_version_id: versionId,
          code: values.code,
          statement: values.statement,
          po_type: values.po_type || undefined,
          order_index: pos.length,
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("Program Outcome created")
      qc.invalidateQueries({ queryKey: queryKeys.programOutcomes.byVersion(versionId) })
      qc.invalidateQueries({ queryKey: queryKeys.programOutcomes.all })
      qc.invalidateQueries({ queryKey: queryKeys.poVersions.all })
      createForm.reset({ code: `PO${pos.length + 2}`, po_type: "", statement: "" })
      setOpen(false)
    },
    onError: () => toast.error("Failed to create Program Outcome"),
  })

  // ── Edit form ────────────────────────────────────────────────────────────

  const editForm = useForm<EditFormValues>({
    resolver: zodResolver(editSchema),
  })

  const editMutation = useMutation({
    mutationFn: async ({ id, values }: { id: string; values: EditFormValues }) => {
      await apiClient.PATCH(`/program-outcomes/${id}` as never, {
        body: {
          statement: values.statement,
          po_type: values.po_type || undefined,
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("Program Outcome updated")
      qc.invalidateQueries({ queryKey: queryKeys.programOutcomes.byVersion(versionId) })
      setEditTarget(null)
    },
    onError: () => toast.error("Failed to update Program Outcome"),
  })

  const openEdit = (po: ProgramOutcome) => {
    setEditTarget(po)
    editForm.reset({
      statement: po.statement,
      po_type: po.po_type || "",
    })
  }

  // ── Delete ───────────────────────────────────────────────────────────────

  const deleteMutation = useMutation({
    mutationFn: async (poId: string) => {
      await apiClient.POST(`/program-outcomes/${poId}/archive` as never, {} as never)
    },
    onSuccess: () => {
      toast.success("Program Outcome deleted")
      qc.invalidateQueries({ queryKey: queryKeys.programOutcomes.byVersion(versionId) })
      qc.invalidateQueries({ queryKey: queryKeys.poVersions.all })
      setDeleteTarget(null)
    },
    onError: () => toast.error("Failed to delete Program Outcome"),
  })

  // ── Columns ──────────────────────────────────────────────────────────────

  const columns: ColumnDef<ProgramOutcome>[] = [
    { accessorKey: "code", header: "Code" },
    {
      accessorKey: "po_type",
      header: "PO Type",
      cell: ({ row }) =>
        row.original.po_type ?? <span className="text-muted-foreground">—</span>,
    },
    {
      accessorKey: "statement",
      header: "Statement",
      cell: ({ row }) => (
        <span className="whitespace-pre-line">{row.original.statement}</span>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <PermissionGate permission="po.update">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-foreground"
              onClick={(e) => { e.stopPropagation(); openEdit(row.original) }}
              title="Edit"
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
          </PermissionGate>
          <PermissionGate permission="po.archive">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-destructive"
              onClick={(e) => { e.stopPropagation(); setDeleteTarget(row.original) }}
              title="Delete"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </PermissionGate>
        </div>
      ),
    },
  ]

  // ── Render ───────────────────────────────────────────────────────────────

  if (!isInitialized || !canManageProgramOutcomes) return null

  if (versionLoading) {
    return <div className="animate-pulse h-40 bg-muted rounded-md" />
  }

  if (!version) {
    return <p className="text-muted-foreground">PO version not found.</p>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/program-outcomes")}
          className="gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
      </div>

      <PageHeader
        title={version.name}
        description={version.description ?? "Manage program outcomes for this version."}
        actions={
          <PermissionGate permission="po.create">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger
                render={
                  <Button>
                    <Plus />
                    Add PO
                  </Button>
                }
              />
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>Add Program Outcome to {version.name}</DialogTitle>
                </DialogHeader>
                <form
                  id="create-po-form"
                  onSubmit={createForm.handleSubmit((v) => createMutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="po-code">Code</Label>
                    <Input id="po-code" {...createForm.register("code")} placeholder="PO1" />
                    {createForm.formState.errors.code && (
                      <p className="text-sm text-destructive">
                        {createForm.formState.errors.code.message}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="po-type">PO Type</Label>
                    <Input id="po-type" {...createForm.register("po_type")} placeholder="e.g. Generic" />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="po-statement">Statement</Label>
                    <Textarea
                      id="po-statement"
                      {...createForm.register("statement")}
                      placeholder="Describe the program outcome..."
                      rows={4}
                      maxLength={500}
                    />
                    {createForm.formState.errors.statement && (
                      <p className="text-sm text-destructive">
                        {createForm.formState.errors.statement.message}
                      </p>
                    )}
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button
                    type="submit"
                    form="create-po-form"
                    disabled={createForm.formState.isSubmitting || createMutation.isPending}
                  >
                    {(createForm.formState.isSubmitting || createMutation.isPending) && (
                      <Loader2 className="animate-spin" />
                    )}
                    Create
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </PermissionGate>
        }
      />

      <DataTable
        columns={columns}
        data={pos}
        loading={posLoading}
        emptyMessage="No program outcomes in this version yet."
      />

      {/* ── Edit Dialog ────────────────────────────────────────────────────── */}
      <Dialog open={!!editTarget} onOpenChange={(o) => { if (!o) setEditTarget(null) }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit {editTarget?.code}</DialogTitle>
          </DialogHeader>
          <form
            id="edit-po-form"
            onSubmit={editForm.handleSubmit((v) => {
              if (editTarget) editMutation.mutate({ id: editTarget.id, values: v })
            })}
            className="space-y-4 py-2"
          >
            <div className="space-y-2">
              <Label htmlFor="edit-po-type">PO Type</Label>
              <Input id="edit-po-type" {...editForm.register("po_type")} placeholder="e.g. Generic" />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-statement">Statement</Label>
              <Textarea
                id="edit-statement"
                {...editForm.register("statement")}
                rows={4}
                maxLength={500}
              />
              {editForm.formState.errors.statement && (
                <p className="text-sm text-destructive">
                  {editForm.formState.errors.statement.message}
                </p>
              )}
            </div>
          </form>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditTarget(null)}>Cancel</Button>
            <Button
              type="submit"
              form="edit-po-form"
              disabled={editForm.formState.isSubmitting || editMutation.isPending}
            >
              {(editForm.formState.isSubmitting || editMutation.isPending) && (
                <Loader2 className="animate-spin" />
              )}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Delete Dialog ──────────────────────────────────────────────────── */}
      <Dialog open={!!deleteTarget} onOpenChange={(o) => { if (!o) setDeleteTarget(null) }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Program Outcome</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Are you sure you want to delete <strong>{deleteTarget?.code}</strong>? This action cannot be undone.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => { if (deleteTarget) deleteMutation.mutate(deleteTarget.id) }}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
