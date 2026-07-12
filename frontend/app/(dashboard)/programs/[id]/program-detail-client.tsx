"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, Plus, Trash2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Combobox } from "@/components/ui/combobox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { formatDate } from "@/lib/utils"

// ── Types ─────────────────────────────────────────────────────────────────────

type ProgramCoordinatorInfo = { user_id: string; full_name: string }
type ProgramCoordinatorHistoryEntry = {
  user_id: string
  full_name: string
  effective_from: string
  effective_to?: string | null
}

type Program = {
  id: string
  title: string
  acronym: string
  department_id: string
  department_name: string
  program_type: string
  minimum_duration_semesters: number
  total_credits: number
  study_mode: string
  description?: string | null
  po_version_id?: string | null
  status: string
  current_coordinator?: ProgramCoordinatorInfo | null
  coordinator_history?: ProgramCoordinatorHistoryEntry[]
}

type ProgramUser = { id: string; full_name: string; employee_id?: string | null }

function userDisplayLabel(user: ProgramUser) {
  return user.employee_id ? `${user.employee_id} - ${user.full_name}` : user.full_name
}

type Department = { id: string; name: string }

type Mission = {
  id: string
  code: string
  statement: string
  order_index: number
  status: string
}

type PEO = {
  id: string
  code: string
  statement: string
  order_index: number
  status: string
}

type ProgramOutcome = {
  id: string
  code: string
  statement: string
}

type PEOPOMapping = { id: string; peo_id: string; program_outcome_id: string }
type PEOMissionMapping = { id: string; peo_id: string; mission_id: string }
type POVersion = { id: string; name: string; is_active: boolean }

// ── Helpers ───────────────────────────────────────────────────────────────────

function byCode<T extends { code: string }>(a: T, b: T): number {
  return a.code.localeCompare(b.code, undefined, { numeric: true })
}

// ── Constants ─────────────────────────────────────────────────────────────────

const PROGRAM_TYPES = [
  { value: "UNDERGRADUATE", label: "Undergraduate" },
  { value: "POSTGRADUATE", label: "Postgraduate" },
  { value: "PHD", label: "PhD" },
]

const STUDY_MODES = [
  { value: "FULL_TIME", label: "Full time" },
  { value: "PART_TIME", label: "Part time" },
]

function formatProgramType(type: string) {
  return PROGRAM_TYPES.find((t) => t.value === type)?.label ?? type
}

function formatStudyMode(mode: string) {
  return STUDY_MODES.find((m) => m.value === mode)?.label ?? mode
}

async function fetchProgramOutcomes(programId: string, poVersionId?: string | null) {
  if (poVersionId) {
    const programVersionUrl = `/program-outcomes?program_id=${programId}&po_version_id=${poVersionId}`
    const { data: programVersionData } = await apiClient.GET(programVersionUrl as never)
    const programVersionPos = ((programVersionData as unknown) as ProgramOutcome[]) ?? []

    if (programVersionPos.length > 0) return programVersionPos

    const { data: versionData } = await apiClient.GET(
      `/program-outcomes?po_version_id=${poVersionId}` as never
    )
    return ((versionData as unknown) as ProgramOutcome[]) ?? []
  }

  const { data } = await apiClient.GET(`/program-outcomes?program_id=${programId}` as never)
  return ((data as unknown) as ProgramOutcome[]) ?? []
}

// ── Edit Program Schema ───────────────────────────────────────────────────────

const programSchema = z.object({
  title: z.string().min(2, "Title required"),
  acronym: z.string().min(1, "Acronym required").max(20),
  department_id: z.string().min(1, "Department required"),
  program_type: z.enum(["UNDERGRADUATE", "POSTGRADUATE", "PHD"], { message: "Type required" }),
  minimum_duration_semesters: z.number().int().min(1).max(20),
  total_credits: z.number().int().min(1).max(500),
  study_mode: z.enum(["FULL_TIME", "PART_TIME"], { message: "Mode required" }),
  description: z.string().optional(),
})
type ProgramFormValues = z.infer<typeof programSchema>

// ── Add Mission / PEO Schema ──────────────────────────────────────────────────

const addItemSchema = z.object({
  code: z.string().min(1, "Code required").max(20),
  statement: z.string().min(5, "Statement required"),
})
type AddItemValues = z.infer<typeof addItemSchema>

// ── Add Mission Dialog ────────────────────────────────────────────────────────

function AddMissionDialog({ programId, existingCount }: { programId: string; existingCount: number }) {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<AddItemValues>({
    resolver: zodResolver(addItemSchema),
    defaultValues: { code: `M${existingCount + 1}`, statement: "" },
  })

  const handleOpenChange = (next: boolean) => {
    if (next) reset({ code: `M${existingCount + 1}`, statement: "" })
    setOpen(next)
  }

  const mutation = useMutation({
    mutationFn: async (values: AddItemValues) => {
      await apiClient.POST("/missions" as never, {
        body: { program_id: programId, ...values, order_index: existingCount },
      } as never)
    },
    onSuccess: () => {
      toast.success("Mission added")
      qc.invalidateQueries({ queryKey: queryKeys.programMissions.byProgram(programId) })
      setOpen(false)
    },
    onError: () => toast.error("Failed to add mission"),
  })

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={<Button size="sm" variant="outline" className="h-7 gap-1 text-xs"><Plus className="h-3 w-3" /> Add</Button>} />
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add Mission</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
          <div className="space-y-2">
            <Label>Code</Label>
            <Input placeholder="M1" {...register("code")} />
            {errors.code && <p className="text-xs text-destructive">{errors.code.message}</p>}
          </div>
          <div className="space-y-2">
            <Label>Statement</Label>
            <Textarea rows={3} placeholder="Describe this mission..." {...register("statement")} />
            {errors.statement && <p className="text-xs text-destructive">{errors.statement.message}</p>}
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={isSubmitting || mutation.isPending}>
              {(isSubmitting || mutation.isPending) && <Loader2 className="animate-spin" />}
              Add Mission
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ── Add PEO Dialog ────────────────────────────────────────────────────────────

function AddPEODialog({ programId, existingCount }: { programId: string; existingCount: number }) {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<AddItemValues>({
    resolver: zodResolver(addItemSchema),
    defaultValues: { code: `PEO${existingCount + 1}`, statement: "" },
  })

  const handleOpenChange = (next: boolean) => {
    if (next) reset({ code: `PEO${existingCount + 1}`, statement: "" })
    setOpen(next)
  }

  const mutation = useMutation({
    mutationFn: async (values: AddItemValues) => {
      await apiClient.POST("/peos" as never, {
        body: { program_id: programId, ...values, order_index: existingCount },
      } as never)
    },
    onSuccess: () => {
      toast.success("PEO added")
      qc.invalidateQueries({ queryKey: queryKeys.peos.byProgram(programId) })
      qc.invalidateQueries({ queryKey: ["peo-po-all-mappings", programId] })
      qc.invalidateQueries({ queryKey: ["peo-mission-all-mappings", programId] })
      setOpen(false)
    },
    onError: () => toast.error("Failed to add PEO"),
  })

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={<Button size="sm" variant="outline" className="h-7 gap-1 text-xs"><Plus className="h-3 w-3" /> Add</Button>} />
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add Program Educational Objective</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
          <div className="space-y-2">
            <Label>Code</Label>
            <Input placeholder="PEO1" {...register("code")} />
            {errors.code && <p className="text-xs text-destructive">{errors.code.message}</p>}
          </div>
          <div className="space-y-2">
            <Label>Statement</Label>
            <Textarea rows={3} placeholder="Describe this PEO..." {...register("statement")} />
            {errors.statement && <p className="text-xs text-destructive">{errors.statement.message}</p>}
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={isSubmitting || mutation.isPending}>
              {(isSubmitting || mutation.isPending) && <Loader2 className="animate-spin" />}
              Add PEO
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ── Mission List Card ─────────────────────────────────────────────────────────

function MissionsCard({ programId }: { programId: string }) {
  const qc = useQueryClient()

  const { data: missions = [], isLoading } = useQuery({
    queryKey: queryKeys.programMissions.byProgram(programId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/programs/${programId}/missions` as never)
      return (data as unknown as Mission[]) ?? []
    },
  })

  const archiveMutation = useMutation({
    mutationFn: async (missionId: string) => {
      await apiClient.POST(`/missions/${missionId}/archive` as never, {} as never)
    },
    onSuccess: () => {
      toast.success("Mission removed")
      qc.invalidateQueries({ queryKey: queryKeys.programMissions.byProgram(programId) })
    },
    onError: () => toast.error("Failed to remove mission"),
  })

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Mission</CardTitle>
          <PermissionGate permission="mission.create">
            <AddMissionDialog programId={programId} existingCount={missions.length} />
          </PermissionGate>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2].map((i) => (
              <div key={i} className="h-10 animate-pulse rounded bg-muted" />
            ))}
          </div>
        ) : missions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No missions defined yet.</p>
        ) : (
          <ul className="space-y-2">
            {[...missions].sort(byCode).map((m) => (
              <li key={m.id} className="flex items-start gap-2 rounded-md border p-2.5">
                <Badge variant="secondary" className="mt-0.5 shrink-0 font-mono text-xs">
                  {m.code}
                </Badge>
                <p className="flex-1 text-sm leading-relaxed">{m.statement}</p>
                <PermissionGate permission="mission.update">
                  <button
                    onClick={() => archiveMutation.mutate(m.id)}
                    disabled={archiveMutation.isPending}
                    className="ml-1 shrink-0 text-muted-foreground hover:text-destructive"
                    title="Remove"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </PermissionGate>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

// ── PEO List Card ─────────────────────────────────────────────────────────────

function PEOsCard({ programId }: { programId: string }) {
  const qc = useQueryClient()

  const { data: peos = [], isLoading } = useQuery({
    queryKey: queryKeys.peos.byProgram(programId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/programs/${programId}/peos` as never)
      return (data as unknown as PEO[]) ?? []
    },
  })

  const archiveMutation = useMutation({
    mutationFn: async (peoId: string) => {
      await apiClient.POST(`/peos/${peoId}/archive` as never, {} as never)
    },
    onSuccess: () => {
      toast.success("PEO removed")
      qc.invalidateQueries({ queryKey: queryKeys.peos.byProgram(programId) })
      qc.invalidateQueries({ queryKey: ["peo-po-all-mappings", programId] })
      qc.invalidateQueries({ queryKey: ["peo-mission-all-mappings", programId] })
    },
    onError: () => toast.error("Failed to remove PEO"),
  })

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Program Educational Objectives (PEO)</CardTitle>
          <PermissionGate permission="peo.create">
            <AddPEODialog programId={programId} existingCount={peos.length} />
          </PermissionGate>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 animate-pulse rounded bg-muted" />
            ))}
          </div>
        ) : peos.length === 0 ? (
          <p className="text-sm text-muted-foreground">No PEOs defined yet.</p>
        ) : (
          <ul className="space-y-2">
            {[...peos].sort(byCode).map((p) => (
              <li key={p.id} className="flex items-start gap-2 rounded-md border p-2.5">
                <Badge variant="secondary" className="mt-0.5 shrink-0 font-mono text-xs">
                  {p.code}
                </Badge>
                <p className="flex-1 text-sm leading-relaxed">{p.statement}</p>
                <PermissionGate permission="peo.update">
                  <button
                    onClick={() => archiveMutation.mutate(p.id)}
                    disabled={archiveMutation.isPending}
                    className="ml-1 shrink-0 text-muted-foreground hover:text-destructive"
                    title="Remove"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </PermissionGate>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

// ── PO List Card (by version) ────────────────────────────────────────────────

function POListCard({
  programId,
  selectedVersion,
  onSelectedVersionChange,
}: {
  programId: string
  selectedVersion: string
  onSelectedVersionChange: (versionId: string) => void
}) {
  const { data: poVersions = [] } = useQuery({
    queryKey: queryKeys.poVersions.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/po-versions" as never)
      return ((data as unknown) as POVersion[]) ?? []
    },
  })

  const { data: pos = [], isLoading } = useQuery({
    queryKey: queryKeys.programOutcomes.list({
      program_id: programId,
      po_version_id: selectedVersion || undefined,
    }),
    queryFn: () => fetchProgramOutcomes(programId, selectedVersion),
  })

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Program Outcomes</CardTitle>
          <div className="w-48">
            <Select
              value={selectedVersion || "__all__"}
              onValueChange={(v) => {
                if (v != null) onSelectedVersionChange(v === "__all__" ? "" : v)
              }}
            >
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder="Select version">
                  {selectedVersion
                    ? poVersions.find((v) => v.id === selectedVersion)?.name ?? "Select version"
                    : "All versions"}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All versions</SelectItem>
                {poVersions.map((v) => (
                  <SelectItem key={v.id} value={v.id}>{v.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => <div key={i} className="h-10 animate-pulse rounded bg-muted" />)}
          </div>
        ) : pos.length === 0 ? (
          <p className="text-sm text-muted-foreground">No program outcomes found.</p>
        ) : (
          <ul className="space-y-2">
            {[...pos].sort((a, b) => a.code.localeCompare(b.code, undefined, { numeric: true })).map((po) => (
              <li key={po.id} className="flex items-start gap-2 rounded-md border p-2.5">
                <Badge variant="secondary" className="mt-0.5 shrink-0 font-mono text-xs">
                  {po.code}
                </Badge>
                <p className="flex-1 text-sm leading-relaxed whitespace-pre-line">{po.statement}</p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

// ── PEO-PO Mapping Card ───────────────────────────────────────────────────────

function PEOPOMappingCard({ programId, poVersionId }: { programId: string; poVersionId?: string | null }) {
  const qc = useQueryClient()

  const { data: peos = [] } = useQuery({
    queryKey: queryKeys.peos.byProgram(programId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/programs/${programId}/peos` as never)
      return (data as unknown as PEO[]) ?? []
    },
  })

  const { data: pos = [] } = useQuery({
    queryKey: queryKeys.programOutcomes.list({
      program_id: programId,
      po_version_id: poVersionId || undefined,
    }),
    queryFn: () => fetchProgramOutcomes(programId, poVersionId),
  })

  const mappingQueries = useQuery({
    queryKey: ["peo-po-all-mappings", programId],
    queryFn: async () => {
      if (peos.length === 0) return {} as Record<string, string[]>
      const results: Record<string, string[]> = {}
      await Promise.all(
        peos.map(async (peo) => {
          const { data } = await apiClient.GET(`/peos/${peo.id}/po-mappings` as never)
          results[peo.id] = ((data as unknown as PEOPOMapping[]) ?? []).map(
            (m) => m.program_outcome_id
          )
        })
      )
      return results
    },
    enabled: peos.length > 0,
  })

  const saveMutation = useMutation({
    mutationFn: async ({ peoId, poIds }: { peoId: string; poIds: string[] }) => {
      await apiClient.PUT(`/peos/${peoId}/po-mappings` as never, {
        body: { po_ids: poIds },
      } as never)
    },
    onSuccess: (_, { peoId }) => {
      qc.invalidateQueries({ queryKey: ["peo-po-all-mappings", programId] })
      qc.invalidateQueries({ queryKey: queryKeys.peos.poMappings(peoId) })
    },
    onError: () => toast.error("Failed to save mapping"),
  })

  const mappings = mappingQueries.data ?? {}

  const toggle = (peoId: string, poId: string) => {
    const current = mappings[peoId] ?? []
    const updated = current.includes(poId)
      ? current.filter((id) => id !== poId)
      : [...current, poId]
    saveMutation.mutate({ peoId, poIds: updated })
  }

  if (peos.length === 0 || pos.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">PEO → PO Mapping</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {peos.length === 0
              ? "Add PEOs above first."
              : "No Program Outcomes found. Create POs from the Program Outcomes page first."}
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">PEO → PO Mapping</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr>
                <th className="pb-2 pr-3 text-left font-medium text-muted-foreground">PEO</th>
                {[...pos].sort(byCode).map((po) => (
                  <th key={po.id} className="pb-2 px-2 text-center font-mono font-medium">
                    {po.code}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...peos].sort(byCode).map((peo) => (
                <tr key={peo.id} className="border-t">
                  <td className="py-2 pr-3">
                    <span className="font-mono font-medium">{peo.code}</span>
                  </td>
                  {[...pos].sort(byCode).map((po) => (
                    <td key={po.id} className="py-2 px-2 text-center">
                      <PermissionGate permission="peo.update" fallback={
                        <input
                          type="checkbox"
                          readOnly
                          checked={(mappings[peo.id] ?? []).includes(po.id)}
                          className="h-4 w-4 cursor-not-allowed accent-primary"
                        />
                      }>
                        <input
                          type="checkbox"
                          checked={(mappings[peo.id] ?? []).includes(po.id)}
                          onChange={() => toggle(peo.id, po.id)}
                          disabled={saveMutation.isPending}
                          className="h-4 w-4 cursor-pointer accent-primary"
                        />
                      </PermissionGate>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

// ── PEO-Mission Mapping Card ──────────────────────────────────────────────────

function PEOMissionMappingCard({ programId }: { programId: string }) {
  const qc = useQueryClient()

  const { data: peos = [] } = useQuery({
    queryKey: queryKeys.peos.byProgram(programId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/programs/${programId}/peos` as never)
      return (data as unknown as PEO[]) ?? []
    },
  })

  const { data: missions = [] } = useQuery({
    queryKey: queryKeys.programMissions.byProgram(programId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/programs/${programId}/missions` as never)
      return (data as unknown as Mission[]) ?? []
    },
  })

  const mappingQueries = useQuery({
    queryKey: ["peo-mission-all-mappings", programId],
    queryFn: async () => {
      if (peos.length === 0) return {} as Record<string, string[]>
      const results: Record<string, string[]> = {}
      await Promise.all(
        peos.map(async (peo) => {
          const { data } = await apiClient.GET(`/peos/${peo.id}/mission-mappings` as never)
          results[peo.id] = ((data as unknown as PEOMissionMapping[]) ?? []).map(
            (m) => m.mission_id
          )
        })
      )
      return results
    },
    enabled: peos.length > 0,
  })

  const saveMutation = useMutation({
    mutationFn: async ({ peoId, missionIds }: { peoId: string; missionIds: string[] }) => {
      await apiClient.PUT(`/peos/${peoId}/mission-mappings` as never, {
        body: { mission_ids: missionIds },
      } as never)
    },
    onSuccess: (_, { peoId }) => {
      qc.invalidateQueries({ queryKey: ["peo-mission-all-mappings", programId] })
      qc.invalidateQueries({ queryKey: queryKeys.peos.missionMappings(peoId) })
    },
    onError: () => toast.error("Failed to save mapping"),
  })

  const mappings = mappingQueries.data ?? {}

  const toggle = (peoId: string, missionId: string) => {
    const current = mappings[peoId] ?? []
    const updated = current.includes(missionId)
      ? current.filter((id) => id !== missionId)
      : [...current, missionId]
    saveMutation.mutate({ peoId, missionIds: updated })
  }

  if (peos.length === 0 || missions.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">PEO → Mission Mapping</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {peos.length === 0
              ? "Add PEOs above to set up mappings."
              : "Add missions above to set up mappings."}
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">PEO → Mission Mapping</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr>
                <th className="pb-2 pr-3 text-left font-medium text-muted-foreground">PEO</th>
                {[...missions].sort(byCode).map((m) => (
                  <th key={m.id} className="pb-2 px-2 text-center font-mono font-medium">
                    {m.code}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...peos].sort(byCode).map((peo) => (
                <tr key={peo.id} className="border-t">
                  <td className="py-2 pr-3">
                    <span className="font-mono font-medium">{peo.code}</span>
                  </td>
                  {[...missions].sort(byCode).map((m) => (
                    <td key={m.id} className="py-2 px-2 text-center">
                      <PermissionGate permission="peo.update" fallback={
                        <input
                          type="checkbox"
                          readOnly
                          checked={(mappings[peo.id] ?? []).includes(m.id)}
                          className="h-4 w-4 cursor-not-allowed accent-primary"
                        />
                      }>
                        <input
                          type="checkbox"
                          checked={(mappings[peo.id] ?? []).includes(m.id)}
                          onChange={() => toggle(peo.id, m.id)}
                          disabled={saveMutation.isPending}
                          className="h-4 w-4 cursor-pointer accent-primary"
                        />
                      </PermissionGate>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Program Coordinator Card ──────────────────────────────────────────────────

function ProgramCoordinatorCard({
  programId,
  currentCoordinator,
  history,
}: {
  programId: string
  currentCoordinator?: ProgramCoordinatorInfo | null
  history?: ProgramCoordinatorHistoryEntry[]
}) {
  const qc = useQueryClient()
  const [coordinatorId, setCoordinatorId] = useState("")

  const { data: users } = useQuery({
    queryKey: queryKeys.users.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/users" as never)
      return ((data as unknown) as ProgramUser[]) ?? []
    },
  })

  const userOptions = (users ?? []).map((u) => ({ value: u.id, label: userDisplayLabel(u) }))

  const assignMutation = useMutation({
    mutationFn: async (user_id: string) => {
      await apiClient.POST(`/programs/${programId}/coordinator` as never, { body: { user_id } } as never)
    },
    onSuccess: () => {
      toast.success("Program Coordinator assigned")
      qc.invalidateQueries({ queryKey: queryKeys.programs.detail(programId) })
      setCoordinatorId("")
    },
    onError: () => toast.error("Failed to assign Program Coordinator"),
  })

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Program Coordinator</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm">
          Current:{" "}
          <span className="font-medium">{currentCoordinator?.full_name ?? "Not assigned"}</span>
        </p>

        <PermissionGate permission="program.update">
          <div className="flex items-end gap-2">
            <div className="flex-1 space-y-2">
              <Label>Assign new Program Coordinator</Label>
              <Combobox
                options={userOptions}
                value={coordinatorId}
                onValueChange={setCoordinatorId}
                placeholder="Search by employee ID or name…"
                searchPlaceholder="Search by employee ID or name…"
                emptyText="No matching users"
                triggerClassName="w-full"
              />
            </div>
            <Button
              disabled={!coordinatorId || assignMutation.isPending}
              onClick={() => coordinatorId && assignMutation.mutate(coordinatorId)}
            >
              {assignMutation.isPending && <Loader2 className="animate-spin" />}
              Assign
            </Button>
          </div>
        </PermissionGate>

        {history && history.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium">History</p>
            <ul className="space-y-2 text-sm">
              {history.map((h, i) => (
                <li key={i} className="flex items-center justify-between border-b pb-2 last:border-0">
                  <span className="font-medium">{h.full_name}</span>
                  <span className="text-muted-foreground">
                    {formatDate(h.effective_from)} — {h.effective_to ? formatDate(h.effective_to) : "Present"}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

interface Props {
  id: string
}

export function ProgramDetailClient({ id }: Props) {
  const qc = useQueryClient()
  const router = useRouter()
  const [selectedPoVersionId, setSelectedPoVersionId] = useState<string | null>(null)

  const deleteMutation = useMutation({
    mutationFn: async () => {
      await apiClient.DELETE(`/programs/${id}` as never)
    },
    onSuccess: () => {
      toast.success("Program deleted")
      qc.invalidateQueries({ queryKey: queryKeys.programs.all })
      router.push("/programs")
    },
  })

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.programs.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/programs/${id}` as never)
      return (data as unknown) as Program
    },
  })

  const { data: departments } = useQuery({
    queryKey: queryKeys.departments.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/departments" as never)
      return ((data as unknown) as { items?: Department[] })?.items ?? ((data as unknown) as Department[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<ProgramFormValues>({
    resolver: zodResolver(programSchema),
    values: data
      ? {
          title: data.title,
          acronym: data.acronym,
          department_id: data.department_id,
          program_type: data.program_type as ProgramFormValues["program_type"],
          minimum_duration_semesters: data.minimum_duration_semesters,
          total_credits: data.total_credits,
          study_mode: data.study_mode as ProgramFormValues["study_mode"],
          description: data.description ?? "",
        }
      : undefined,
  })

  const mutation = useMutation({
    mutationFn: async (values: ProgramFormValues) => {
      await apiClient.PATCH(`/programs/${id}` as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Program updated")
      qc.invalidateQueries({ queryKey: queryKeys.programs.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.programs.all })
    },
    onError: () => toast.error("Failed to update program"),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Program not found.</p>

  const effectivePoVersionId = selectedPoVersionId ?? data.po_version_id ?? ""

  return (
    <div className="space-y-6">
      <PageHeader
        title={data.title}
        description={`${data.acronym} · ${formatProgramType(data.program_type)} · ${data.department_name}`}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={data.status} />
            <PermissionGate permission="program.delete">
              <Button
                variant="destructive"
                size="sm"
                disabled={deleteMutation.isPending}
                onClick={() => {
                  if (window.confirm(`Permanently delete "${data.title}"? This cannot be undone.`))
                    deleteMutation.mutate()
                }}
              >
                {deleteMutation.isPending ? <Loader2 className="animate-spin" /> : <Trash2 className="h-4 w-4" />}
                Delete
              </Button>
            </PermissionGate>
          </div>
        }
      />

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle>Program Details</CardTitle>
            <Badge variant="secondary" className="w-fit">
              {data.acronym}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <PermissionGate
            permission="program.update"
            fallback={
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <DetailItem label="Title" value={data.title} className="sm:col-span-2" />
                <DetailItem label="Department" value={data.department_name} />
                <DetailItem label="Type" value={formatProgramType(data.program_type)} />
                <DetailItem label="Semesters" value={`${data.minimum_duration_semesters}`} />
                <DetailItem label="Credits" value={`${data.total_credits}`} />
                <DetailItem label="Mode" value={formatStudyMode(data.study_mode)} />
                <DetailItem
                  label="Vision"
                  value={data.description || "No vision added yet."}
                  className="sm:col-span-2 lg:col-span-4"
                />
              </div>
            }
          >
            <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-5">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="title">Title</Label>
                  <Input id="title" {...register("title")} />
                  {errors.title && <p className="text-sm text-destructive">{errors.title.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="acronym">Acronym</Label>
                  <Input id="acronym" {...register("acronym")} />
                  {errors.acronym && <p className="text-sm text-destructive">{errors.acronym.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label>Department</Label>
                  <Controller
                    name="department_id"
                    control={control}
                    render={({ field }) => (
                      <Select value={field.value ?? ""} onValueChange={field.onChange}>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select department">
                            {(value: string) => value
                              ? ((departments ?? []).find((d) => d.id === value)?.name ?? value)
                              : null}
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {(departments ?? []).map((d) => (
                            <SelectItem key={d.id} value={d.id}>
                              {d.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                  {errors.department_id && (
                    <p className="text-sm text-destructive">{errors.department_id.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label>Type</Label>
                  <Controller
                    name="program_type"
                    control={control}
                    render={({ field }) => (
                      <Select value={field.value ?? ""} onValueChange={field.onChange}>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select type">
                            {(value: string) => value
                              ? (PROGRAM_TYPES.find((t) => t.value === value)?.label ?? value)
                              : null}
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {PROGRAM_TYPES.map((t) => (
                            <SelectItem key={t.value} value={t.value}>
                              {t.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                  {errors.program_type && (
                    <p className="text-sm text-destructive">{errors.program_type.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="minimum_duration_semesters">No. of Semesters</Label>
                  <Input
                    id="minimum_duration_semesters"
                    type="number"
                    min={1}
                    max={20}
                    {...register("minimum_duration_semesters", { valueAsNumber: true })}
                  />
                  {errors.minimum_duration_semesters && (
                    <p className="text-sm text-destructive">{errors.minimum_duration_semesters.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="total_credits">Total Credits</Label>
                  <Input
                    id="total_credits"
                    type="number"
                    min={1}
                    max={500}
                    {...register("total_credits", { valueAsNumber: true })}
                  />
                  {errors.total_credits && (
                    <p className="text-sm text-destructive">{errors.total_credits.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label>Mode</Label>
                  <Controller
                    name="study_mode"
                    control={control}
                    render={({ field }) => (
                      <Select value={field.value ?? ""} onValueChange={field.onChange}>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select mode">
                            {(value: string) => value
                              ? (STUDY_MODES.find((m) => m.value === value)?.label ?? value)
                              : null}
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {STUDY_MODES.map((m) => (
                            <SelectItem key={m.value} value={m.value}>
                              {m.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                  {errors.study_mode && (
                    <p className="text-sm text-destructive">{errors.study_mode.message}</p>
                  )}
                </div>
                <div className="space-y-2 md:col-span-2 xl:col-span-4">
                  <Label htmlFor="description">Vision</Label>
                  <Textarea id="description" rows={3} {...register("description")} />
                </div>
              </div>
              <Button type="submit" disabled={!isDirty || isSubmitting || mutation.isPending}>
                {(isSubmitting || mutation.isPending) && <Loader2 className="animate-spin" />}
                Save Changes
              </Button>
            </form>
          </PermissionGate>
        </CardContent>
      </Card>

      <ProgramCoordinatorCard
        programId={id}
        currentCoordinator={data.current_coordinator}
        history={data.coordinator_history}
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="space-y-6">
          <MissionsCard programId={id} />
          <PEOsCard programId={id} />
          <PEOMissionMappingCard programId={id} />
        </div>

        <div className="space-y-6">
          <POListCard
            programId={id}
            selectedVersion={effectivePoVersionId}
            onSelectedVersionChange={(versionId) => setSelectedPoVersionId(versionId)}
          />
          <PEOPOMappingCard programId={id} poVersionId={effectivePoVersionId} />
        </div>
      </div>
    </div>
  )
}

function DetailItem({
  label,
  value,
  className,
}: {
  label: string
  value: string
  className?: string
}) {
  return (
    <div className={className}>
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm leading-relaxed">{value}</p>
    </div>
  )
}
