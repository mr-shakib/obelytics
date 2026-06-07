"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Check, X, Loader2 } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { useState } from "react"

type ApprovalItem = {
  id: string
  subject: string
  description: string
  entity_type: string
  entity_id: string
  requested_by: string
  requested_at: string
  status: "PENDING" | "APPROVED" | "REJECTED"
}

export function ApprovalsClient() {
  const qc = useQueryClient()
  const [remarks, setRemarks] = useState<Record<string, string>>({})

  const { data: items, isLoading } = useQuery({
    queryKey: queryKeys.approvals.inbox,
    queryFn: async () => {
      const { data } = await apiClient.GET("/approvals/inbox" as never)
      return ((data as unknown) as { items?: ApprovalItem[] })?.items ?? ((data as unknown) as ApprovalItem[]) ?? []
    },
  })

  const actMutation = useMutation({
    mutationFn: async ({ id, action, remark }: { id: string; action: "approve" | "reject"; remark?: string }) => {
      await apiClient.POST(`/approvals/${id}/${action}` as never, {
        body: { remark },
      } as never)
    },
    onSuccess: () => {
      toast.success("Action recorded")
      qc.invalidateQueries({ queryKey: queryKeys.approvals.inbox })
    },
    onError: () => toast.error("Failed to process approval"),
  })

  const pending = (items ?? []).filter((i) => i.status === "PENDING")
  const done = (items ?? []).filter((i) => i.status !== "PENDING")

  return (
    <div className="space-y-6">
      <PageHeader
        title="Approvals"
        description="Review and action pending approval requests."
      />

      {isLoading && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-muted animate-pulse rounded-md" />)}
        </div>
      )}

      {!isLoading && pending.length === 0 && (
        <p className="text-sm text-muted-foreground">No pending approvals.</p>
      )}

      {pending.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Pending ({pending.length})</h2>
          {pending.map((item) => (
            <Card key={item.id}>
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-medium text-sm">{item.subject}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Requested by <span className="font-medium">{item.requested_by}</span> ·{" "}
                      {formatDistanceToNow(new Date(item.requested_at), { addSuffix: true })}
                    </p>
                  </div>
                  <Badge variant="secondary">{item.entity_type}</Badge>
                </div>
                <Textarea
                  placeholder="Optional remark..."
                  value={remarks[item.id] ?? ""}
                  onChange={(e) => setRemarks((prev) => ({ ...prev, [item.id]: e.target.value }))}
                  rows={2}
                  className="text-xs"
                />
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => actMutation.mutate({ id: item.id, action: "approve", remark: remarks[item.id] })}
                    disabled={actMutation.isPending}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {actMutation.isPending ? <Loader2 className="animate-spin" /> : <Check />}
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => actMutation.mutate({ id: item.id, action: "reject", remark: remarks[item.id] })}
                    disabled={actMutation.isPending}
                  >
                    <X /> Reject
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {done.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Actioned ({done.length})</h2>
          {done.map((item) => (
            <Card key={item.id} className="opacity-70">
              <CardContent className="p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium text-sm">{item.subject}</p>
                  <p className="text-xs text-muted-foreground">{item.description}</p>
                </div>
                <Badge variant={item.status === "APPROVED" ? "default" : "destructive"}>
                  {item.status}
                </Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
