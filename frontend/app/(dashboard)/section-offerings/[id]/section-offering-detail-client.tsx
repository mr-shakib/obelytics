"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"
import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type SectionOffering = {
  id: string
  code: string
  course_name: string
  course_id: string
  batch_name: string
  batch_id: string
  term_name: string
  academic_term_id: string
  section: string
  faculty_name?: string
  enrolled_count?: number
  status: string
}

interface Props {
  id: string
}

export function SectionOfferingDetailClient({ id }: Props) {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.sectionOfferings.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/section-offerings/${id}` as never)
      return (data as unknown) as SectionOffering
    },
  })

  const lockMutation = useMutation({
    mutationFn: async () => {
      await apiClient.POST(`/section-offerings/${id}/lock` as never, {} as never)
    },
    onSuccess: () => {
      toast.success("Section offering locked")
      qc.invalidateQueries({ queryKey: queryKeys.sectionOfferings.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.sectionOfferings.all })
    },
    onError: () => toast.error("Failed to lock section offering"),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Section offering not found.</p>

  const canLock = data.status === "ACTIVE"

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title={data.code}
        description={`${data.course_name} · ${data.batch_name} · ${data.term_name}`}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={data.status} />
            <Button variant="outline" size="sm" render={<Link href={`/assessments?offering_id=${id}`} />}>
              Assessments
            </Button>
            <Button variant="outline" size="sm" render={<Link href={`/results/${id}`} />}>
              Results
            </Button>
          </div>
        }
      />

      <Card>
        <CardHeader><CardTitle>Details</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex gap-4">
            <span className="text-muted-foreground w-36">Course</span>
            <span>{data.course_name}</span>
          </div>
          <div className="flex gap-4">
            <span className="text-muted-foreground w-36">Batch</span>
            <span>{data.batch_name}</span>
          </div>
          <div className="flex gap-4">
            <span className="text-muted-foreground w-36">Term</span>
            <span>{data.term_name}</span>
          </div>
          <div className="flex gap-4">
            <span className="text-muted-foreground w-36">Section</span>
            <span>{data.section}</span>
          </div>
          {data.faculty_name && (
            <div className="flex gap-4">
              <span className="text-muted-foreground w-36">Faculty</span>
              <span>{data.faculty_name}</span>
            </div>
          )}
          {data.enrolled_count !== undefined && (
            <div className="flex gap-4">
              <span className="text-muted-foreground w-36">Enrolled</span>
              <span>{data.enrolled_count} students</span>
            </div>
          )}
        </CardContent>
      </Card>

      {canLock && (
        <PermissionGate permission="assessment.lock">
          <Card>
            <CardHeader><CardTitle>Actions</CardTitle></CardHeader>
            <CardContent>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => lockMutation.mutate()}
                disabled={lockMutation.isPending}
              >
                {lockMutation.isPending && <Loader2 className="animate-spin" />}
                Lock Offering
              </Button>
              <p className="text-xs text-muted-foreground mt-2">
                Locking prevents further marks entry and enables result computation.
              </p>
            </CardContent>
          </Card>
        </PermissionGate>
      )}
    </div>
  )
}
