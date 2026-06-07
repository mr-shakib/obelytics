"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, Play, FileText } from "lucide-react"
import Link from "next/link"
import { formatDistanceToNow } from "date-fns"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type ReportDefinition = { id: string; name: string; description?: string; params_schema?: object }
type ReportRun = {
  id: string
  definition_id: string
  definition_name: string
  status: "PENDING" | "RUNNING" | "DONE" | "FAILED"
  created_at: string
  completed_at?: string
  output_url?: string
}

const STATUS_VARIANT: Record<ReportRun["status"], "default" | "secondary" | "destructive"> = {
  PENDING: "secondary",
  RUNNING: "secondary",
  DONE: "default",
  FAILED: "destructive",
}

export function ReportsClient() {
  const qc = useQueryClient()
  const [runningDef, setRunningDef] = useState<string | null>(null)

  const { data: definitions } = useQuery({
    queryKey: queryKeys.reports.definitions,
    queryFn: async () => {
      const { data } = await apiClient.GET("/reports/definitions" as never)
      return ((data as unknown) as { items?: ReportDefinition[] })?.items ?? ((data as unknown) as ReportDefinition[]) ?? []
    },
  })

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: queryKeys.reports.runs(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/reports/runs" as never)
      return ((data as unknown) as { items?: ReportRun[] })?.items ?? ((data as unknown) as ReportRun[]) ?? []
    },
    refetchInterval: (query) => {
      const data = query.state.data as ReportRun[] | undefined
      const hasActive = data?.some((r) => r.status === "RUNNING" || r.status === "PENDING")
      return hasActive ? 5000 : false
    },
  })

  const triggerMutation = useMutation({
    mutationFn: async (defId: string) => {
      await apiClient.POST("/reports/runs" as never, {
        body: { definition_id: defId },
      } as never)
    },
    onSuccess: () => {
      toast.success("Report generation started")
      qc.invalidateQueries({ queryKey: queryKeys.reports.runs() })
      setRunningDef(null)
    },
    onError: () => {
      toast.error("Failed to generate report")
      setRunningDef(null)
    },
  })

  return (
    <div className="space-y-8">
      <PageHeader
        title="Reports"
        description="Generate accreditation and program outcome reports."
      />

      <div>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">Available Reports</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(definitions ?? []).map((def) => (
            <Card key={def.id}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  {def.name}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {def.description && (
                  <p className="text-xs text-muted-foreground">{def.description}</p>
                )}
                <PermissionGate permission="reports.generate">
                  <Button
                    size="sm"
                    className="w-full"
                    disabled={runningDef === def.id || triggerMutation.isPending}
                    onClick={() => {
                      setRunningDef(def.id)
                      triggerMutation.mutate(def.id)
                    }}
                  >
                    {runningDef === def.id ? <Loader2 className="animate-spin" /> : <Play />}
                    Generate
                  </Button>
                </PermissionGate>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      <div>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">Recent Runs</h2>

        {runsLoading && (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => <div key={i} className="h-14 bg-muted animate-pulse rounded-md" />)}
          </div>
        )}

        {!runsLoading && (runs ?? []).length === 0 && (
          <p className="text-sm text-muted-foreground">No report runs yet.</p>
        )}

        <div className="space-y-2">
          {(runs ?? []).map((run) => (
            <div key={run.id} className="flex items-center justify-between p-3 rounded-md border text-sm">
              <div>
                <p className="font-medium">{run.definition_name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={STATUS_VARIANT[run.status]}>
                  {run.status === "RUNNING" && <Loader2 className="animate-spin mr-1 h-3 w-3" />}
                  {run.status}
                </Badge>
                {run.status === "DONE" && (
                  <Button variant="outline" size="sm" render={<Link href={`/reports/${run.id}`} />}>
                    View
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
