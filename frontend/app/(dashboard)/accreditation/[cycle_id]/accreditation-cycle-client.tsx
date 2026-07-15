"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, ArrowLeft, FileText, Plus, Link2 } from "lucide-react"
import Link from "next/link"
import { format } from "date-fns"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type CycleCriterion = {
  id: string
  criterion_code: string
  title: string
  status: "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED"
  assigned_to_user_id?: string
  assigned_to?: string
}

type AccreditationCycleDetail = {
  id: string
  name: string
  body: string
  status: "ACTIVE" | "CLOSED" | "DRAFT"
  start_date: string
  end_date?: string
  program_name: string
  program_id: string
  criteria: CycleCriterion[]
  completion_pct?: number
}

type UserOption = { id: string; full_name: string }
type ProgramOutcomeOption = { id: string; code: string; statement: string }
type POMapping = { id: string; program_outcome_id: string }

interface Props {
  cycleId: string
}

const CRITERION_VARIANT: Record<CycleCriterion["status"], "default" | "secondary" | "destructive"> = {
  NOT_STARTED: "secondary",
  IN_PROGRESS: "default",
  COMPLETED: "default",
}

const STATUS_OPTIONS: CycleCriterion["status"][] = ["NOT_STARTED", "IN_PROGRESS", "COMPLETED"]

const criterionSchema = z.object({
  code: z.string().min(1, "Code required").max(30),
  title: z.string().min(1, "Title required"),
  description: z.string().optional(),
})
type CriterionForm = z.infer<typeof criterionSchema>

function AddCriterionDialog({ cycleId, existingCount }: { cycleId: string; existingCount: number }) {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<CriterionForm>({
    resolver: zodResolver(criterionSchema),
    defaultValues: { code: `SO${existingCount + 1}`, title: "", description: "" },
  })

  const handleOpenChange = (next: boolean) => {
    if (next) reset({ code: `SO${existingCount + 1}`, title: "", description: "" })
    setOpen(next)
  }

  const mutation = useMutation({
    mutationFn: async (values: CriterionForm) => {
      await apiClient.POST(`/accreditation/cycles/${cycleId}/criteria` as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Criterion added")
      qc.invalidateQueries({ queryKey: queryKeys.accreditation.cycle(cycleId) })
      setOpen(false)
    },
    onError: () => toast.error("Failed to add criterion"),
  })

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={<Button size="sm" variant="outline"><Plus /> Add Criterion</Button>} />
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>Add Criterion</DialogTitle></DialogHeader>
        <form id="criterion-form" onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="crit-code">Code</Label>
            <Input id="crit-code" placeholder="SO1" {...register("code")} />
            {errors.code && <p className="text-xs text-destructive">{errors.code.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="crit-title">Title</Label>
            <Input id="crit-title" placeholder="e.g. Engineering Problem Solving" {...register("title")} />
            {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="crit-desc">Description</Label>
            <Textarea id="crit-desc" rows={3} {...register("description")} />
          </div>
        </form>
        <DialogFooter showCloseButton>
          <Button type="submit" form="criterion-form" disabled={mutation.isPending || isSubmitting}>
            {mutation.isPending && <Loader2 className="animate-spin" />} Add
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function POMappingDialog({ criterionId, criterionCode, programId }: { criterionId: string; criterionCode: string; programId: string }) {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()

  const { data: pos = [] } = useQuery({
    queryKey: ["program-outcomes", programId],
    enabled: open,
    queryFn: async () => {
      const { data } = await apiClient.GET(`/program-outcomes?program_id=${programId}` as never)
      return ((data as unknown) as ProgramOutcomeOption[]) ?? []
    },
  })

  const { data: mappings = [] } = useQuery({
    queryKey: ["accreditation-po-mappings", criterionId],
    enabled: open,
    queryFn: async () => {
      const { data } = await apiClient.GET(`/accreditation/criteria/${criterionId}/po-mappings` as never)
      return ((data as unknown) as POMapping[]) ?? []
    },
  })

  const mappedIds = new Set(mappings.map((m) => m.program_outcome_id))

  const mapMutation = useMutation({
    mutationFn: async (poId: string) => {
      await apiClient.POST(`/accreditation/criteria/${criterionId}/po-mappings` as never, {
        body: { program_outcome_id: poId },
      } as never)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accreditation-po-mappings", criterionId] }),
    onError: () => toast.error("Failed to map PO"),
  })

  const unmapMutation = useMutation({
    mutationFn: async (poId: string) => {
      await apiClient.DELETE(`/accreditation/criteria/${criterionId}/po-mappings/${poId}` as never, {} as never)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accreditation-po-mappings", criterionId] }),
    onError: () => toast.error("Failed to unmap PO"),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="sm" variant="ghost" className="h-7 gap-1 text-xs"><Link2 className="h-3 w-3" /> POs</Button>} />
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>Map Program Outcomes — {criterionCode}</DialogTitle></DialogHeader>
        <div className="space-y-2 py-2 max-h-80 overflow-y-auto">
          {pos.length === 0 ? (
            <p className="text-sm text-muted-foreground">No program outcomes found for this program.</p>
          ) : pos.map((po) => (
            <label key={po.id} className="flex items-start gap-2 rounded-md border p-2.5 cursor-pointer">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 accent-primary"
                checked={mappedIds.has(po.id)}
                onChange={() => mappedIds.has(po.id) ? unmapMutation.mutate(po.id) : mapMutation.mutate(po.id)}
                disabled={mapMutation.isPending || unmapMutation.isPending}
              />
              <span className="text-sm">
                <span className="font-mono font-medium mr-1.5">{po.code}</span>
                {po.statement}
              </span>
            </label>
          ))}
        </div>
        <DialogFooter showCloseButton>
          <Button type="button" onClick={() => setOpen(false)}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function AccreditationCycleClient({ cycleId }: Props) {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.accreditation.cycle(cycleId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/accreditation/cycles/${cycleId}` as never)
      return (data as unknown) as AccreditationCycleDetail
    },
  })

  const { data: users } = useQuery({
    queryKey: queryKeys.users.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/users" as never)
      return ((data as unknown) as UserOption[]) ?? []
    },
  })

  const generateReportMutation = useMutation({
    mutationFn: async () => {
      await apiClient.POST(`/accreditation/cycles/${cycleId}/generate-report` as never, {} as never)
    },
    onSuccess: () => {
      toast.success("Report generation started. Check Reports for progress.")
    },
    onError: () => toast.error("Failed to generate report"),
  })

  const closeMutation = useMutation({
    mutationFn: async () => {
      await apiClient.POST(`/accreditation/cycles/${cycleId}/close` as never, {} as never)
    },
    onSuccess: () => {
      toast.success("Cycle closed")
      qc.invalidateQueries({ queryKey: queryKeys.accreditation.cycle(cycleId) })
    },
    onError: () => toast.error("Failed to close cycle"),
  })

  const updateCriterionMutation = useMutation({
    mutationFn: async ({ id, patch }: { id: string; patch: Record<string, string | null> }) => {
      await apiClient.PATCH(`/accreditation/criteria/${id}` as never, { body: patch } as never)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.accreditation.cycle(cycleId) }),
    onError: () => toast.error("Failed to update criterion"),
  })

  if (isLoading) return <div className="animate-pulse h-48 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Accreditation cycle not found.</p>

  const done = (data.criteria ?? []).filter((c) => c.status === "COMPLETED").length
  const total = data.criteria?.length ?? 0

  return (
    <div className="space-y-6">
      <PageHeader
        title={data.name}
        description={`${data.body} · ${data.program_name}`}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant={data.status === "ACTIVE" ? "default" : "secondary"}>{data.status}</Badge>
            <Button variant="outline" size="sm" nativeButton={false} render={<Link href="/accreditation" />}>
              <ArrowLeft /> Back
            </Button>
            <PermissionGate permission="accreditation.manage">
              <Button
                variant="outline"
                size="sm"
                onClick={() => generateReportMutation.mutate()}
                disabled={generateReportMutation.isPending}
              >
                {generateReportMutation.isPending ? <Loader2 className="animate-spin" /> : <FileText />}
                Generate SSR
              </Button>
            </PermissionGate>
            {data.status === "ACTIVE" && (
              <PermissionGate permission="accreditation.manage">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => closeMutation.mutate()}
                  disabled={closeMutation.isPending}
                >
                  {closeMutation.isPending && <Loader2 className="animate-spin" />}
                  Close Cycle
                </Button>
              </PermissionGate>
            )}
          </div>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground font-medium">Period</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm font-medium">
              {format(new Date(data.start_date), "MMM yyyy")}
              {data.end_date && ` — ${format(new Date(data.end_date), "MMM yyyy")}`}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground font-medium">Criteria Progress</CardTitle></CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{done}/{total}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground font-medium">Completion</CardTitle></CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{data.completion_pct ?? (total > 0 ? Math.round((done / total) * 100) : 0)}%</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-sm">Criteria Checklist</CardTitle>
          <PermissionGate permission="accreditation.manage">
            <AddCriterionDialog cycleId={cycleId} existingCount={total} />
          </PermissionGate>
        </CardHeader>
        <CardContent className="p-0">
          {total === 0 ? (
            <p className="text-sm text-muted-foreground p-4">No criteria added yet.</p>
          ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50 text-left">
                <th className="px-4 py-2 font-medium">Code</th>
                <th className="px-4 py-2 font-medium">Title</th>
                <th className="px-4 py-2 font-medium">Program Outcomes</th>
                <th className="px-4 py-2 font-medium">Assigned To</th>
                <th className="px-4 py-2 font-medium text-right">Status</th>
              </tr>
            </thead>
            <tbody>
              {(data.criteria ?? []).map((c) => (
                <tr key={c.id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-2 font-medium">{c.criterion_code}</td>
                  <td className="px-4 py-2">{c.title}</td>
                  <td className="px-4 py-2">
                    <POMappingDialog criterionId={c.id} criterionCode={c.criterion_code} programId={data.program_id} />
                  </td>
                  <td className="px-4 py-2 text-xs">
                    <PermissionGate
                      permission="accreditation.manage"
                      fallback={<span className="text-muted-foreground">{c.assigned_to ?? "—"}</span>}
                    >
                      <Select
                        value={c.assigned_to_user_id ?? ""}
                        onValueChange={(v) => updateCriterionMutation.mutate({ id: c.id, patch: { assigned_to_user_id: (v as string) || null } })}
                      >
                        <SelectTrigger className="h-7 w-36 text-xs">
                          <SelectValue placeholder="Unassigned">
                            {() => c.assigned_to ?? "Unassigned"}
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {(users ?? []).map((u) => (
                            <SelectItem key={u.id} value={u.id}>{u.full_name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </PermissionGate>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <PermissionGate
                      permission="accreditation.manage"
                      fallback={
                        <Badge variant={CRITERION_VARIANT[c.status]} className="text-xs">
                          {c.status.replace("_", " ")}
                        </Badge>
                      }
                    >
                      <Select
                        value={c.status}
                        onValueChange={(v) => updateCriterionMutation.mutate({ id: c.id, patch: { status: v as string } })}
                      >
                        <SelectTrigger className="h-7 w-32 text-xs ml-auto">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {STATUS_OPTIONS.map((s) => (
                            <SelectItem key={s} value={s}>{s.replace("_", " ")}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </PermissionGate>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
