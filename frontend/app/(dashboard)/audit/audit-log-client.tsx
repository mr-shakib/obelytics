"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { format } from "date-fns"
import { PageHeader } from "@/components/shared/page-header"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

type AuditLog = {
  id: string
  actor_name: string
  actor_email: string
  action: string
  entity_type: string
  entity_id?: string
  timestamp: string
  ip_address?: string
  changes?: Record<string, { from: unknown; to: unknown }>
}

const ACTION_COLORS: Record<string, string> = {
  CREATE: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  UPDATE: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  DELETE: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  LOGIN: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
}

export function AuditLogClient() {
  const [search, setSearch] = useState("")
  const [expanded, setExpanded] = useState<string | null>(null)
  const [page, setPage] = useState(1)

  const filters = {
    q: search || undefined,
    page,
    page_size: 25,
  }

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.audit.logs(filters),
    queryFn: async () => {
      const params = new URLSearchParams()
      if (search) params.set("q", search)
      params.set("page", String(page))
      params.set("page_size", "25")
      const { data } = await apiClient.GET(`/audit/logs?${params.toString()}` as never)
      return (data as unknown) as { items: AuditLog[]; total: number; page: number; pages: number }
    },
  })

  const logs = data?.items ?? []
  const totalPages = data?.pages ?? 1

  return (
    <div className="space-y-4">
      <PageHeader
        title="Audit Log"
        description="Complete audit trail of all system actions."
      />

      <div className="flex gap-3">
        <Input
          placeholder="Search by actor, action, or entity..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          className="max-w-sm"
        />
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => <div key={i} className="h-12 bg-muted animate-pulse rounded-md" />)}
        </div>
      )}

      {!isLoading && logs.length === 0 && (
        <p className="text-sm text-muted-foreground">No audit logs found.</p>
      )}

      <div className="space-y-1">
        {logs.map((log) => (
          <div key={log.id}>
            <div
              className="flex items-center gap-3 p-3 rounded-md border text-sm cursor-pointer hover:bg-muted/30 transition-colors"
              onClick={() => setExpanded(expanded === log.id ? null : log.id)}
            >
              <span className={cn(
                "px-1.5 py-0.5 rounded text-xs font-medium shrink-0",
                ACTION_COLORS[log.action] ?? "bg-muted text-muted-foreground"
              )}>
                {log.action}
              </span>
              <span className="font-medium shrink-0">{log.actor_name}</span>
              <span className="text-muted-foreground text-xs">{log.actor_email}</span>
              <Badge variant="secondary" className="text-xs shrink-0">{log.entity_type}</Badge>
              {log.entity_id && (
                <span className="text-muted-foreground text-xs font-mono shrink-0">{log.entity_id.slice(0, 8)}…</span>
              )}
              <span className="text-muted-foreground text-xs ml-auto shrink-0">
                {format(new Date(log.timestamp), "dd MMM yyyy HH:mm")}
              </span>
            </div>

            {expanded === log.id && log.changes && Object.keys(log.changes).length > 0 && (
              <Card className="mt-1 mb-1 ml-4">
                <CardContent className="p-3">
                  <p className="text-xs font-medium text-muted-foreground mb-2">Changes</p>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-muted-foreground">
                        <th className="text-left font-medium pb-1 pr-4">Field</th>
                        <th className="text-left font-medium pb-1 pr-4">Before</th>
                        <th className="text-left font-medium pb-1">After</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(log.changes).map(([field, { from, to }]) => (
                        <tr key={field} className="border-t">
                          <td className="py-1 pr-4 font-medium">{field}</td>
                          <td className="py-1 pr-4 text-muted-foreground">{String(from ?? "—")}</td>
                          <td className="py-1">{String(to ?? "—")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            )}
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}
