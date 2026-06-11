"use client"

import { useQuery } from "@tanstack/react-query"
import { Download } from "lucide-react"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type StudentResult = {
  enrollment_id: string
  student_name: string
  student_id: string
  total_marks: number
  max_marks: number
  percentage: number
  grade?: string
  co_attainments?: Record<string, number>
}

type OfferingResults = {
  offering_id: string
  course_name: string
  term_name: string
  batch_name: string
  section: string
  class_avg: number
  co_averages?: Record<string, number>
  results: StudentResult[]
}

interface Props {
  offeringId: string
}

function GradeCell({ pct }: { pct: number }) {
  const color =
    pct >= 80 ? "default" :
    pct >= 60 ? "secondary" :
    "destructive"
  return <Badge variant={color}>{pct.toFixed(1)}%</Badge>
}

export function ResultsClient({ offeringId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.results.byOffering(offeringId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/results/${offeringId}` as never)
      return (data as unknown) as OfferingResults
    },
  })

  if (isLoading) return <div className="animate-pulse h-48 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">No results found.</p>

  const coKeys = data.co_averages ? Object.keys(data.co_averages) : []

  return (
    <div className="space-y-6">
      <PageHeader
        title={data.course_name}
        description={`${data.batch_name} · ${data.term_name} · Section ${data.section}`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Download /> Export
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground font-medium">Students</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">{data.results.length}</p></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground font-medium">Class Average</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">{data.class_avg.toFixed(1)}%</p></CardContent>
        </Card>
        {coKeys.slice(0, 2).map((co) => (
          <Card key={co}>
            <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground font-medium">{co} Attainment</CardTitle></CardHeader>
            <CardContent><p className="text-2xl font-bold">{(data.co_averages![co] ?? 0).toFixed(1)}%</p></CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader><CardTitle className="text-sm">Student Results</CardTitle></CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50 text-left">
                  <th className="px-4 py-2 font-medium">Student</th>
                  <th className="px-4 py-2 font-medium text-right">Marks</th>
                  <th className="px-4 py-2 font-medium text-right">%</th>
                  {data.results[0]?.grade !== undefined && (
                    <th className="px-4 py-2 font-medium text-right">Grade</th>
                  )}
                  {coKeys.map((co) => (
                    <th key={co} className="px-4 py-2 font-medium text-right">{co}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.results.map((r) => (
                  <tr key={r.enrollment_id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-2">
                      <div>
                        <p className="font-medium">{r.student_name}</p>
                        <p className="text-xs text-muted-foreground">{r.student_id}</p>
                      </div>
                    </td>
                    <td className="px-4 py-2 text-right">
                      {r.total_marks}/{r.max_marks}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <GradeCell pct={r.percentage} />
                    </td>
                    {r.grade !== undefined && (
                      <td className="px-4 py-2 text-right font-medium">{r.grade}</td>
                    )}
                    {coKeys.map((co) => (
                      <td key={co} className="px-4 py-2 text-right text-muted-foreground text-xs">
                        {r.co_attainments?.[co]?.toFixed(1) ?? "—"}%
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
