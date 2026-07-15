"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, Play, TrendingUp } from "lucide-react"
import Link from "next/link"
import { formatDistanceToNow } from "date-fns"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Program = { id: string; name: string; code: string }
type AttainmentRun = {
  id: string
  program_id: string
  program_name: string
  academic_term_id?: string
  term_name?: string
  status: "PENDING" | "RUNNING" | "DONE" | "FAILED"
  triggered_at: string
  completed_at?: string
  triggered_by?: string
}

const STATUS_COLORS: Record<AttainmentRun["status"], string> = {
  PENDING: "secondary",
  RUNNING: "default",
  DONE: "default",
  FAILED: "destructive",
}

export function AttainmentClient() {
  const qc = useQueryClient()
  const [programId, setProgramId] = useState<string>("")

  const { data: programs } = useQuery({
    queryKey: queryKeys.programs.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/programs" as never)
      return ((data as unknown) as { items?: Program[] })?.items ?? ((data as unknown) as Program[]) ?? []
    },
  })

  const { data: runs, isLoading } = useQuery({
    queryKey: queryKeys.attainment.list({ program_id: programId || undefined }),
    queryFn: async () => {
      const url = programId ? `/attainment/runs?program_id=${programId}` : "/attainment/runs"
      const { data } = await apiClient.GET(url as never)
      return ((data as unknown) as { items?: AttainmentRun[] })?.items ?? ((data as unknown) as AttainmentRun[]) ?? []
    },
    refetchInterval: (query) => {
      const data = query.state.data as AttainmentRun[] | undefined
      const hasRunning = data?.some((r) => r.status === "RUNNING" || r.status === "PENDING")
      return hasRunning ? 3000 : false
    },
  })

  const triggerMutation = useMutation({
    mutationFn: async () => {
      if (!programId) throw new Error("Select a program first")
      await apiClient.POST("/attainment/runs" as never, {
        body: { program_id: programId },
      } as never)
    },
    onSuccess: () => {
      toast.success("Attainment calculation triggered")
      qc.invalidateQueries({ queryKey: queryKeys.attainment.all })
    },
    onError: (e: Error) => toast.error(e.message || "Failed to trigger attainment"),
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Attainment"
        description="Compute and track course and program outcome attainment."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" nativeButton={false} render={<Link href="/attainment/trends" />}>
              <TrendingUp /> Trends
            </Button>
            <PermissionGate permission="attainment.initiate">
              <Button
                size="sm"
                onClick={() => triggerMutation.mutate()}
                disabled={!programId || triggerMutation.isPending}
              >
                {triggerMutation.isPending ? <Loader2 className="animate-spin" /> : <Play />}
                Run Computation
              </Button>
            </PermissionGate>
          </div>
        }
      />

      <div className="flex gap-4 items-center">
        <div className="w-64">
          <Select
            value={programId}
            onValueChange={(v) => setProgramId((v as string | null) ?? "")}
          >
            <SelectTrigger>
              <SelectValue placeholder="All programs" />
            </SelectTrigger>
            <SelectContent>
              {(programs ?? []).map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.code} — {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 bg-muted animate-pulse rounded-md" />
          ))}
        </div>
      )}

      {!isLoading && (runs ?? []).length === 0 && (
        <p className="text-sm text-muted-foreground">No attainment runs found.</p>
      )}

      <div className="space-y-3">
        {(runs ?? []).map((run) => (
          <Card key={run.id} className="hover:shadow-sm transition-shadow">
            <CardContent className="p-4 flex items-center justify-between">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{run.program_name}</span>
                  {run.term_name && (
                    <span className="text-muted-foreground text-xs">· {run.term_name}</span>
                  )}
                  <Badge variant={STATUS_COLORS[run.status] as "default" | "secondary" | "destructive"}>
                    {run.status === "RUNNING" && <Loader2 className="animate-spin mr-1 h-3 w-3" />}
                    {run.status}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Triggered {formatDistanceToNow(new Date(run.triggered_at), { addSuffix: true })}
                  {run.triggered_by && ` by ${run.triggered_by}`}
                </p>
              </div>
              {run.status === "DONE" && (
                <Button variant="outline" size="sm" nativeButton={false} render={<Link href={`/attainment/${run.id}`} />}>
                  View Results
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
