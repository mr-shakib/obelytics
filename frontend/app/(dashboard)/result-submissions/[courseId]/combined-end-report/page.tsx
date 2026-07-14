"use client"

import { useState } from "react"
import { useParams, useRouter, useSearchParams } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { toast } from "sonner"
import { ArrowLeft, Download, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui/table"
import { PageHeader } from "@/components/shared/page-header"
import { apiClient } from "@/lib/api/client"

const GRADES = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "F"]

type CombinedData = {
  course_code: string
  course_title: string
  credits: number
  batch_name: string
  term_name: string
  term_season: string
  term_year: number
  sections: { section_name: string; section_offering_id: string; end_report_status: string | null }[]
  total_sections: number
  submitted_sections: number
  combined_grade_distribution: Record<string, number>
  combined_co_attainment: Record<string, number>
  // Computed from actual marks + the course's CO-PO mapping, averaged across
  // submitted sections the same way combined_co_attainment is.
  combined_po_attainment: Record<string, number>
  all_unattained_explanations: { co_code: string; reason: string; suggestion: string; section_name: string }[]
  section_feedbacks: { section_name: string; feedback: string }[]
  co_threshold: number
  unattained_cos: string[]
}

type Justification = { reason: string; suggestion: string }

export default function CombinedEndReportPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const courseId = params.courseId as string
  const batchId = searchParams.get("batch_id") ?? ""
  const termId = searchParams.get("term_id") ?? ""
  const code = searchParams.get("code") ?? ""
  const title = searchParams.get("title") ?? ""
  const [mlFeedback, setMlFeedback] = useState("")
  const [justifications, setJustifications] = useState<Record<string, Justification>>({})
  const [isDownloading, setIsDownloading] = useState(false)

  const setJustification = (coCode: string, field: keyof Justification, value: string) =>
    setJustifications((prev) => {
      const current = prev[coCode] ?? { reason: "", suggestion: "" }
      return { ...prev, [coCode]: { ...current, [field]: value } }
    })

  const { data, isLoading } = useQuery({
    queryKey: ["end-reports", "combined", courseId, batchId, termId],
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/end-reports/combined?course_id=${courseId}&batch_id=${batchId}&academic_term_id=${termId}` as never
      )
      return (data as unknown) as CombinedData
    },
    enabled: !!batchId && !!termId,
  })

  async function handleDownloadPdf() {
    setIsDownloading(true)
    try {
      const unattained_justifications = (data?.unattained_cos ?? []).map((co_code) => ({
        co_code,
        reason: justifications[co_code]?.reason ?? "",
        suggestion: justifications[co_code]?.suggestion ?? "",
      }))
      const { data: blob, error } = await apiClient.POST(
        `/end-reports/combined/pdf` as never,
        {
          body: {
            course_id: courseId,
            batch_id: batchId,
            academic_term_id: termId,
            ml_feedback: mlFeedback,
            unattained_justifications,
          },
          parseAs: "blob",
        } as never
      )
      if (error || !blob) {
        toast.error("Failed to generate combined end report PDF")
        return
      }
      const url = URL.createObjectURL(blob as Blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${data?.course_code ?? "course"}_combined_end_report.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      toast.error("Failed to generate combined end report PDF")
    } finally {
      setIsDownloading(false)
    }
  }

  if (isLoading) return <div className="h-64 animate-pulse bg-muted rounded-lg" />

  if (!data) return <p className="text-muted-foreground">No data available.</p>

  const totalStudents = Object.values(data.combined_grade_distribution).reduce((s, n) => s + n, 0)
  const allSubmitted = data.submitted_sections === data.total_sections

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <PageHeader
        title="Combined Course End Report"
        description={`${code || data.course_code} — ${title || data.course_title} · ${data.batch_name} · ${data.term_name}`}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownloadPdf}
              disabled={isDownloading || !allSubmitted}
            >
              {isDownloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              Download Combined PDF
            </Button>
            <Button variant="outline" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
          </div>
        }
      />

      {/* Section Submission Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Section Submission Status</CardTitle>
          <CardDescription>
            {data.submitted_sections} of {data.total_sections} sections have submitted their end reports.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {data.sections.map((s) => (
              <Badge
                key={s.section_offering_id}
                variant={s.end_report_status === "SUBMITTED" ? "default" : "secondary"}
              >
                Section {s.section_name}: {s.end_report_status === "SUBMITTED" ? "Submitted" : "Pending"}
              </Badge>
            ))}
          </div>
          {!allSubmitted && (
            <p className="text-sm text-amber-600 mt-3">
              All sections must submit their end reports before you can download the combined PDF.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Combined Grade Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Combined Grade Distribution</CardTitle>
          <CardDescription>
            Aggregated across all {data.submitted_sections} submitted section(s). Total: {totalStudents} students.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {totalStudents > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  {GRADES.map((g) => (
                    <TableHead key={g} className="text-center">{g}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  {GRADES.map((g) => {
                    const count = data.combined_grade_distribution[g] ?? 0
                    const pct = totalStudents > 0 ? ((count / totalStudents) * 100).toFixed(1) : "0.0"
                    return (
                      <TableCell key={g} className="text-center">
                        <div className="font-medium">{count}</div>
                        <div className="text-xs text-muted-foreground">{pct}%</div>
                      </TableCell>
                    )
                  })}
                </TableRow>
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No grade distribution data yet.</p>
          )}
        </CardContent>
      </Card>

      {/* Combined CO Attainment */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Combined CO Attainment (Average)</CardTitle>
        </CardHeader>
        <CardContent>
          {Object.keys(data.combined_co_attainment).length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {Object.entries(data.combined_co_attainment).map(([coCode, pct]) => {
                const attained = pct >= 50
                return (
                  <div key={coCode} className="text-center p-3 rounded-lg border">
                    <div className="font-mono font-semibold text-lg">{coCode}</div>
                    <div className={`text-2xl font-bold ${attained ? "text-green-600" : "text-red-600"}`}>
                      {pct}%
                    </div>
                    <Badge variant={attained ? "default" : "destructive"} className="mt-1 text-xs">
                      {attained ? "Attained" : "Not Attained"}
                    </Badge>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No CO attainment data.</p>
          )}
        </CardContent>
      </Card>

      {/* Combined PO Attainment */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Combined PO Attainment (Average)</CardTitle>
          <CardDescription>Computed from marks and the course&apos;s CO-PO mapping, averaged across submitted sections.</CardDescription>
        </CardHeader>
        <CardContent>
          {Object.keys(data.combined_po_attainment).length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {Object.entries(data.combined_po_attainment).map(([poCode, pct]) => {
                const attained = pct >= 50
                return (
                  <div key={poCode} className="text-center p-3 rounded-lg border">
                    <div className="font-mono font-semibold text-lg">{poCode}</div>
                    <div className={`text-2xl font-bold ${attained ? "text-green-600" : "text-red-600"}`}>
                      {pct}%
                    </div>
                    <Badge variant={attained ? "default" : "destructive"} className="mt-1 text-xs">
                      {attained ? "Attained" : "Not Attained"}
                    </Badge>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No program outcomes mapped for this course.</p>
          )}
        </CardContent>
      </Card>

      {/* Unattained CO Explanations (from all sections) */}
      {data.all_unattained_explanations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Unattained CO Explanations</CardTitle>
            <CardDescription>Collected from all section teachers.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-24">CO</TableHead>
                  <TableHead className="w-20">Section</TableHead>
                  <TableHead>Reasons</TableHead>
                  <TableHead>Suggestions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.all_unattained_explanations.map((exp, idx) => (
                  <TableRow key={idx}>
                    <TableCell><Badge variant="destructive">{exp.co_code}</Badge></TableCell>
                    <TableCell className="text-xs">{exp.section_name}</TableCell>
                    <TableCell className="whitespace-normal text-sm">{exp.reason || "—"}</TableCell>
                    <TableCell className="whitespace-normal text-sm">{exp.suggestion || "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Section Teacher Feedback */}
      {data.section_feedbacks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Section Teacher Feedback</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.section_feedbacks.map((sf, idx) => (
              <div key={idx} className="rounded-lg border p-3">
                <Badge variant="outline" className="mb-2">Section {sf.section_name}</Badge>
                <p className="text-sm whitespace-pre-wrap">{sf.feedback}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* ML Unattained CO Justification */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Unattained CO Justification (Module Leader)</CardTitle>
          <CardDescription>
            {data.unattained_cos.length > 0
              ? `These COs have combined attainment below the ${data.co_threshold}% threshold. Provide your justification — it appears in Section 5 of the PDF.`
              : "All COs meet the attainment threshold. The PDF will state that all COs are attained."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {data.unattained_cos.length === 0 ? (
            <p className="text-sm text-green-600">All COs attained — no justification required.</p>
          ) : (
            data.unattained_cos.map((coCode) => (
              <div key={coCode} className="rounded-lg border p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant="destructive">{coCode}</Badge>
                  <span className="text-sm text-muted-foreground">
                    {data.combined_co_attainment[coCode]}% attained
                  </span>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Identified reasons behind CO &lt; {data.co_threshold}%</Label>
                  <Textarea
                    rows={2}
                    value={justifications[coCode]?.reason ?? ""}
                    onChange={(e) => setJustification(coCode, "reason", e.target.value)}
                    placeholder="Why did this CO fall below the threshold?"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Suggestions for improvement</Label>
                  <Textarea
                    rows={2}
                    value={justifications[coCode]?.suggestion ?? ""}
                    onChange={(e) => setJustification(coCode, "suggestion", e.target.value)}
                    placeholder="How can attainment of this CO be improved?"
                  />
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* ML Feedback */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Module Leader Feedback & Justification</CardTitle>
          <CardDescription>Enter your overall feedback for the combined course end report.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label>Your Feedback</Label>
            <Textarea
              value={mlFeedback}
              onChange={(e) => setMlFeedback(e.target.value)}
              rows={4}
              placeholder="Enter your overall assessment, observations, and justification for this course..."
            />
          </div>
        </CardContent>
      </Card>

      {/* Download */}
      <div className="flex justify-end gap-3">
        <Button
          onClick={handleDownloadPdf}
          disabled={isDownloading || !allSubmitted}
        >
          {isDownloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
          Download Combined End Report PDF
        </Button>
      </div>
    </div>
  )
}
