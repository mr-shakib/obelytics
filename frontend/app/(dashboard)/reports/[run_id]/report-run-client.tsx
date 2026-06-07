"use client"

import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, Download, Loader2 } from "lucide-react"
import Link from "next/link"
import { format } from "date-fns"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type ReportRunDetail = {
  id: string
  definition_name: string
  status: "PENDING" | "RUNNING" | "DONE" | "FAILED"
  created_at: string
  completed_at?: string
  output_url?: string
  params?: Record<string, unknown>
  summary?: Record<string, unknown>
  error?: string
}

interface Props {
  runId: string
}

export function ReportRunClient({ runId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.reports.run(runId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/reports/runs/${runId}` as never)
      return (data as unknown) as ReportRunDetail
    },
    refetchInterval: (query) => {
      const d = query.state.data as ReportRunDetail | undefined
      return d?.status === "RUNNING" || d?.status === "PENDING" ? 3000 : false
    },
  })

  if (isLoading) return <div className="animate-pulse h-48 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Report run not found.</p>

  const isActive = data.status === "PENDING" || data.status === "RUNNING"

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader
        title={data.definition_name}
        description={data.created_at ? `Generated ${format(new Date(data.created_at), "PPP")}` : ""}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant={data.status === "DONE" ? "default" : data.status === "FAILED" ? "destructive" : "secondary"}>
              {isActive && <Loader2 className="animate-spin mr-1 h-3 w-3" />}
              {data.status}
            </Badge>
            <Button variant="outline" size="sm" render={<Link href="/reports" />}>
              <ArrowLeft /> Reports
            </Button>
            {data.output_url && (
              <Button size="sm" render={<a href={data.output_url} download />}>
                <Download /> Download
              </Button>
            )}
          </div>
        }
      />

      {isActive && (
        <Card>
          <CardContent className="p-6 flex items-center gap-3 text-muted-foreground">
            <Loader2 className="animate-spin h-5 w-5" />
            <span className="text-sm">Report is being generated…</span>
          </CardContent>
        </Card>
      )}

      {data.error && (
        <Card className="border-destructive/50">
          <CardHeader><CardTitle className="text-destructive text-sm">Error</CardTitle></CardHeader>
          <CardContent>
            <pre className="text-xs whitespace-pre-wrap text-muted-foreground">{data.error}</pre>
          </CardContent>
        </Card>
      )}

      {data.summary && Object.keys(data.summary).length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-sm">Summary</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              {Object.entries(data.summary).map(([k, v]) => (
                <div key={k} className="flex gap-4">
                  <span className="text-muted-foreground w-40 shrink-0 capitalize">{k.replace(/_/g, " ")}</span>
                  <span className="font-medium">{String(v)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {data.params && Object.keys(data.params).length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-sm">Parameters</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-1 text-sm">
              {Object.entries(data.params).map(([k, v]) => (
                <div key={k} className="flex gap-4">
                  <span className="text-muted-foreground w-40 shrink-0 capitalize">{k.replace(/_/g, " ")}</span>
                  <span className="text-muted-foreground">{String(v)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
