"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import Link from "next/link"
import { Loader2, ChevronDown, ChevronRight, BookOpen, Play, CheckCircle, Settings2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { usePermission } from "@/hooks/use-permission"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { formatDate } from "@/lib/utils"

type SemesterCourse = {
  course_id: string
  code: string
  title: string
  credits: number
  theory_hours: number
  lab_hours: number
  is_elective: boolean
}

type SemesterPlanItem = {
  term_number: number
  academic_term_id: string
  name: string
  year: number
  season: string
  start_date: string
  end_date: string
  status: string
  total_credits: number
  courses: SemesterCourse[]
}

type Batch = {
  id: string
  name: string
  curriculum_id: string
  intake_year: number | null
  start_date: string | null
  term_system: string | null
  num_semesters: number | null
  status: string
}

const schema = z.object({
  name: z.string().min(1, "Name is required"),
})
type FormValues = z.infer<typeof schema>

interface Props {
  id: string
}

const SEASON_ACCENT: Record<string, { border: string; label: string }> = {
  SPRING: { border: "border-l-green-400",  label: "bg-green-100 text-green-800" },
  SUMMER: { border: "border-l-yellow-400", label: "bg-yellow-100 text-yellow-800" },
  FALL:   { border: "border-l-orange-400", label: "bg-orange-100 text-orange-800" },
  WINTER: { border: "border-l-blue-400",   label: "bg-blue-100 text-blue-800" },
}

function SemesterRow({
  item,
  batchId,
  canManage,
  onStatusChange,
  changingId,
}: {
  item: SemesterPlanItem
  batchId: string
  canManage: boolean
  onStatusChange: (termId: string, status: "ACTIVE" | "COMPLETED") => void
  changingId: string | null
}) {
  const [open, setOpen] = useState(false)
  const accent = SEASON_ACCENT[item.season] ?? { border: "border-l-muted", label: "" }
  const busy = changingId === item.academic_term_id

  return (
    <div className={`border-l-4 rounded-r-lg border border-border ${accent.border} overflow-hidden`}>
      <div className="flex items-center justify-between px-4 py-3 hover:bg-muted/50 transition-colors">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-3 flex-1 text-left"
        >
          {open ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
          )}
          <div>
            <span className="font-medium text-sm">Semester {item.term_number}</span>
            <span className="text-muted-foreground text-sm ml-2">·</span>
            <span className="text-sm ml-2">{item.name}</span>
          </div>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${accent.label}`}>
            {item.season}
          </span>
        </button>

        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <span className="hidden sm:block">{formatDate(item.start_date)} – {formatDate(item.end_date)}</span>
          <span className="flex items-center gap-1">
            <BookOpen className="h-3.5 w-3.5" />
            {item.courses.length}
          </span>
          <span className="font-semibold text-foreground">{item.total_credits} cr</span>
          <StatusBadge status={item.status} />

          {canManage && item.status === "UPCOMING" && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1"
              disabled={busy}
              onClick={() => onStatusChange(item.academic_term_id, "ACTIVE")}
            >
              {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
              Start
            </Button>
          )}
          {canManage && item.status === "ACTIVE" && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1"
              disabled={busy}
              onClick={() => onStatusChange(item.academic_term_id, "COMPLETED")}
            >
              {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle className="h-3 w-3" />}
              Complete
            </Button>
          )}
          <Link
            href={`/batches/${batchId}/terms/${item.academic_term_id}`}
            className="inline-flex items-center gap-1 h-7 px-2 text-xs rounded-md border border-border hover:bg-muted transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            <Settings2 className="h-3 w-3" />
            Sections
          </Link>
        </div>
      </div>

      {open && (
        <div className="border-t border-border bg-muted/20">
          {item.courses.length === 0 ? (
            <p className="px-6 py-3 text-sm text-muted-foreground italic">
              No courses assigned to this semester in the curriculum.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground text-xs uppercase">
                  <th className="px-6 py-2 text-left font-medium">Code</th>
                  <th className="px-4 py-2 text-left font-medium">Title</th>
                  <th className="px-4 py-2 text-center font-medium">Credits</th>
                  <th className="px-4 py-2 text-center font-medium">Theory</th>
                  <th className="px-4 py-2 text-center font-medium">Lab</th>
                  <th className="px-4 py-2 text-left font-medium">Type</th>
                </tr>
              </thead>
              <tbody>
                {item.courses.map((c) => (
                  <tr key={c.course_id} className="border-b border-border/50 last:border-0 hover:bg-muted/40">
                    <td className="px-6 py-2.5 font-mono font-medium">{c.code}</td>
                    <td className="px-4 py-2.5">{c.title}</td>
                    <td className="px-4 py-2.5 text-center">{c.credits}</td>
                    <td className="px-4 py-2.5 text-center text-muted-foreground">{c.theory_hours}h</td>
                    <td className="px-4 py-2.5 text-center text-muted-foreground">{c.lab_hours}h</td>
                    <td className="px-4 py-2.5">
                      {c.is_elective ? (
                        <Badge variant="outline" className="text-xs">Elective</Badge>
                      ) : (
                        <Badge variant="secondary" className="text-xs">Core</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-muted/30">
                  <td colSpan={2} className="px-6 py-2 text-xs text-muted-foreground">Total</td>
                  <td className="px-4 py-2 text-center font-semibold text-sm">{item.total_credits}</td>
                  <td colSpan={3} />
                </tr>
              </tfoot>
            </table>
          )}
        </div>
      )}
    </div>
  )
}

export function BatchDetailClient({ id }: Props) {
  const qc = useQueryClient()
  const canManage = usePermission("curriculum.update")
  const [changingTermId, setChangingTermId] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.batches.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/batches/${id}` as never)
      return (data as unknown) as Batch
    },
  })

  const { data: semesterPlan = [], isLoading: planLoading } = useQuery({
    queryKey: queryKeys.batches.semesterPlan(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/batches/${id}/semester-plan` as never)
      return ((data as unknown) as SemesterPlanItem[]) ?? []
    },
    enabled: !!data,
  })

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: data ? { name: data.name } : undefined,
  })

  const batchMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.PATCH(`/batches/${id}` as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Batch updated")
      qc.invalidateQueries({ queryKey: queryKeys.batches.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.batches.all })
    },
    onError: () => toast.error("Failed to update batch"),
  })

  const statusMutation = useMutation({
    mutationFn: async ({ termId, status }: { termId: string; status: string }) => {
      setChangingTermId(termId)
      await apiClient.PATCH(`/academic-terms/${termId}` as never, { body: { status } } as never)
    },
    onSuccess: (_, { status }) => {
      const label = status === "ACTIVE" ? "started" : "completed"
      toast.success(`Semester ${label}`)
      qc.invalidateQueries({ queryKey: queryKeys.batches.semesterPlan(id) })
      qc.invalidateQueries({ queryKey: queryKeys.academicTerms.all })
    },
    onError: () => toast.error("Failed to update semester status"),
    onSettled: () => setChangingTermId(null),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Batch not found.</p>

  const totalCreditsAll = semesterPlan.reduce((s, t) => s + t.total_credits, 0)

  return (
    <div className="max-w-5xl space-y-6">
      <PageHeader
        title={data.name}
        description={[
          data.term_system,
          data.num_semesters ? `${data.num_semesters} semesters` : null,
          data.start_date ? `from ${data.start_date.slice(0, 7)}` : null,
        ].filter(Boolean).join(" · ")}
        actions={<StatusBadge status={data.status} />}
      />

      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Term System",     value: data.term_system ?? "—" },
          { label: "Total Semesters", value: data.num_semesters ?? "—" },
          { label: "Total Credits",   value: totalCreditsAll || "—" },
        ].map(({ label, value }) => (
          <Card key={label} className="py-4">
            <CardContent className="text-center">
              <p className="text-2xl font-bold">{value}</p>
              <p className="text-xs text-muted-foreground mt-1">{label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Semester plan accordion */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Semester Plan</span>
            <span className="text-sm font-normal text-muted-foreground">
              Click a semester to see its courses
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {planLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-12 animate-pulse bg-muted rounded-lg" />
              ))}
            </div>
          ) : semesterPlan.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              No semester calendar generated yet.
            </p>
          ) : (
            semesterPlan.map((item) => (
              <SemesterRow
                key={item.term_number}
                item={item}
                batchId={id}
                canManage={canManage}
                onStatusChange={(termId, status) => statusMutation.mutate({ termId, status })}
                changingId={changingTermId}
              />
            ))
          )}
        </CardContent>
      </Card>

      <PermissionGate permission="batch.create">
        <Card>
          <CardHeader><CardTitle>Edit Batch</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit((v) => batchMutation.mutate(v))} className="space-y-4 max-w-sm">
              <div className="space-y-2">
                <Label htmlFor="name">Batch Name</Label>
                <Input id="name" {...register("name")} />
                {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
              </div>
              <Button type="submit" disabled={!isDirty || isSubmitting || batchMutation.isPending}>
                {(isSubmitting || batchMutation.isPending) && <Loader2 className="animate-spin" />}
                Save Changes
              </Button>
            </form>
          </CardContent>
        </Card>
      </PermissionGate>
    </div>
  )
}
