"use client"

import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import { formatDistanceToNow } from "date-fns"
import { ArrowRight } from "lucide-react"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { StatusBadge } from "@/components/shared/status-badge"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type InboxItem = {
  entity_type: string
  entity_id: string
  description: string
  status: string
  submitted_at: string | null
  section_offering_id?: string | null
}

type InboxResponse = {
  pending_result_publications: InboxItem[]
  pending_course_outcomes: InboxItem[]
  pending_co_po_mapping_sets: InboxItem[]
  total_count: number
}

function SubmittedAt({ value }: { value: string | null }) {
  if (!value) return null
  return <span>Submitted {formatDistanceToNow(new Date(value), { addSuffix: true })}</span>
}

export function ApprovalsClient() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.approvals.inbox,
    queryFn: async () => {
      const { data } = await apiClient.GET("/approval/inbox" as never)
      return (data as unknown) as InboxResponse
    },
  })

  const resultItems = data?.pending_result_publications ?? []
  const coItems = data?.pending_course_outcomes ?? []
  const mappingItems = data?.pending_co_po_mapping_sets ?? []
  const total = data?.total_count ?? 0

  return (
    <div className="space-y-6">
      <PageHeader
        title="Approvals"
        description="Review and action items pending your approval."
      />

      {isLoading && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-muted animate-pulse rounded-md" />)}
        </div>
      )}

      {!isLoading && total === 0 && (
        <p className="text-sm text-muted-foreground">No pending approvals.</p>
      )}

      {resultItems.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Section Result Reports ({resultItems.length})
          </h2>
          {resultItems.map((item) => (
            <Card key={item.entity_id}>
              <CardContent className="p-4 flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <p className="font-medium text-sm">{item.description}</p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <StatusBadge status={item.status} />
                    <SubmittedAt value={item.submitted_at} />
                  </div>
                </div>
                {item.section_offering_id && (
                  <Button
                    size="sm"
                    nativeButton={false}
                    render={
                      <Link
                        href={`/results/${item.section_offering_id}?label=${encodeURIComponent(item.description)}`}
                      />
                    }
                  >
                    Review <ArrowRight />
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {coItems.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Course Outcomes ({coItems.length})
          </h2>
          {coItems.map((item) => (
            <Card key={item.entity_id}>
              <CardContent className="p-4 flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <p className="font-medium text-sm">{item.description}</p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <StatusBadge status={item.status} />
                    <SubmittedAt value={item.submitted_at} />
                  </div>
                </div>
                <Button size="sm" variant="outline" nativeButton={false} render={<Link href={`/course-outcomes/${item.entity_id}`} />}>
                  View <ArrowRight />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {mappingItems.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            CO-PO Mapping Sets ({mappingItems.length})
          </h2>
          {mappingItems.map((item) => (
            <Card key={item.entity_id}>
              <CardContent className="p-4 flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <p className="font-medium text-sm">{item.description}</p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <SubmittedAt value={item.submitted_at} />
                  </div>
                </div>
                <Badge variant="secondary">{item.status}</Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
