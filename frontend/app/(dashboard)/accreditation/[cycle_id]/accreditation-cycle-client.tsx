"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, ArrowLeft, FileText } from "lucide-react"
import Link from "next/link"
import { format } from "date-fns"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type CycleCriterion = {
  id: string
  criterion_code: string
  title: string
  status: "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED"
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

interface Props {
  cycleId: string
}

const CRITERION_VARIANT: Record<CycleCriterion["status"], "default" | "secondary" | "destructive"> = {
  NOT_STARTED: "secondary",
  IN_PROGRESS: "default",
  COMPLETED: "default",
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
            <Button variant="outline" size="sm" render={<Link href="/accreditation" />}>
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

      {total > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-sm">Criteria Checklist</CardTitle></CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50 text-left">
                  <th className="px-4 py-2 font-medium">Code</th>
                  <th className="px-4 py-2 font-medium">Title</th>
                  <th className="px-4 py-2 font-medium">Assigned To</th>
                  <th className="px-4 py-2 font-medium text-right">Status</th>
                </tr>
              </thead>
              <tbody>
                {(data.criteria ?? []).map((c) => (
                  <tr key={c.id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-2 font-medium">{c.criterion_code}</td>
                    <td className="px-4 py-2">{c.title}</td>
                    <td className="px-4 py-2 text-muted-foreground text-xs">{c.assigned_to ?? "—"}</td>
                    <td className="px-4 py-2 text-right">
                      <Badge variant={CRITERION_VARIANT[c.status]} className="text-xs">
                        {c.status.replace("_", " ")}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
