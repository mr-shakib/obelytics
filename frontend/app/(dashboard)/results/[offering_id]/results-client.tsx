"use client"

import { useState } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { ArrowLeft, Check, Download, Loader2, Undo2 } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { useHasAnyPermission } from "@/hooks/use-permission"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { AttainmentPanel } from "../../my-sections/[id]/attainment-panel"
import { MarksCoPoPanel } from "../../my-sections/[id]/marks-co-po-panel"

type ResultPublication = {
  id: string
  section_offering_id: string
  status: string
  submitted_at: string | null
  ml_approved_at: string | null
  ml_rejection_comment: string | null
  pc_approved_at: string | null
  published_at: string | null
}

interface Props {
  offeringId: string
}

export function ResultsClient({ offeringId }: Props) {
  const qc = useQueryClient()
  const searchParams = useSearchParams()
  const label = searchParams.get("label")

  const canApprove = useHasAnyPermission(["result.approve.ml"])
  const canReject = useHasAnyPermission(["result.reject.ml"])

  const [rejectComment, setRejectComment] = useState("")
  const [isDownloading, setIsDownloading] = useState(false)

  const { data: result, isLoading } = useQuery({
    queryKey: queryKeys.results.byOffering(offeringId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/results/${offeringId}` as never)
      return (data as unknown) as ResultPublication
    },
  })

  const invalidate = () => qc.invalidateQueries({ queryKey: queryKeys.results.byOffering(offeringId) })

  const approveMutation = useMutation({
    mutationFn: async () => {
      await apiClient.POST(`/results/${offeringId}/approve-ml` as never, {} as never)
    },
    onSuccess: () => {
      toast.success("Section report approved")
      invalidate()
    },
    onError: () => toast.error("Failed to approve section report"),
  })

  const rejectMutation = useMutation({
    mutationFn: async () => {
      await apiClient.POST(`/results/${offeringId}/reject-ml` as never, {
        body: { comment: rejectComment },
      } as never)
    },
    onSuccess: () => {
      toast.success("Sent back to section teacher")
      setRejectComment("")
      invalidate()
    },
    onError: () => toast.error("Failed to send section report back"),
  })

  async function handleDownloadPdf() {
    setIsDownloading(true)
    try {
      const { data: blob, error } = await apiClient.GET(
        `/marksheets/${offeringId}/report-pdf` as never,
        { parseAs: "blob" } as never
      )
      if (error || !blob) {
        toast.error("Failed to generate section report")
        return
      }
      const url = URL.createObjectURL(blob as Blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "section_report.pdf"
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      toast.error("Failed to generate section report")
    } finally {
      setIsDownloading(false)
    }
  }

  if (isLoading) return <div className="animate-pulse h-48 bg-muted rounded-md" />
  if (!result) return <p className="text-muted-foreground">Result not found.</p>

  return (
    <div className="space-y-6">
      <PageHeader
        title={label ?? "Section Result Review"}
        description={result.submitted_at ? `Submitted ${new Date(result.submitted_at).toLocaleString()}` : undefined}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={result.status} />
            <Button variant="outline" size="sm" onClick={handleDownloadPdf} disabled={isDownloading}>
              {isDownloading ? <Loader2 className="animate-spin" /> : <Download />} Download PDF
            </Button>
            <Button variant="outline" size="sm" nativeButton={false} render={<Link href="/approvals" />}>
              <ArrowLeft /> Back to Approvals
            </Button>
          </div>
        }
      />

      {result.status === "DRAFT" && (
        <Alert>
          <AlertTitle>Not yet submitted</AlertTitle>
          <AlertDescription>
            The section teacher has not submitted this section&apos;s results for review yet.
          </AlertDescription>
        </Alert>
      )}

      {result.status === "DRAFT" && result.ml_rejection_comment && (
        <Alert className="border-amber-300 bg-amber-50 text-amber-900">
          <AlertTitle>Sent back for changes</AlertTitle>
          <AlertDescription className="text-amber-800">{result.ml_rejection_comment}</AlertDescription>
        </Alert>
      )}

      {result.status === "SUBMITTED" && (canApprove || canReject) && (
        <Card>
          <CardHeader><CardTitle className="text-sm">Review this section&apos;s report</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Approve to accept the results as final, or send it back to the section teacher with a comment
              describing what needs to change. Sending back will unlock the section for editing.
            </p>
            <div className="flex items-center gap-2">
              {canApprove && (
                <Button onClick={() => approveMutation.mutate()} disabled={approveMutation.isPending}>
                  {approveMutation.isPending ? <Loader2 className="animate-spin" /> : <Check />} Approve
                </Button>
              )}
            </div>
            {canReject && (
              <div className="space-y-2">
                <Textarea
                  placeholder="Explain what needs to change before this can be approved..."
                  value={rejectComment}
                  onChange={(e) => setRejectComment(e.target.value)}
                  rows={3}
                />
                <Button
                  variant="destructive"
                  onClick={() => rejectMutation.mutate()}
                  disabled={rejectMutation.isPending || rejectComment.trim().length === 0}
                >
                  {rejectMutation.isPending ? <Loader2 className="animate-spin" /> : <Undo2 />} Send Back
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <MarksCoPoPanel sectionOfferingId={offeringId} />
      <AttainmentPanel sectionOfferingId={offeringId} />
    </div>
  )
}
