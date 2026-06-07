"use client"

import { useQuery } from "@tanstack/react-query"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { StatusBadge } from "@/components/shared/status-badge"
import { apiClient } from "@/lib/api/client"
import { cn } from "@/lib/utils"

interface COResult {
  co_code: string
  co_statement: string
  attainment_percentage: number
  threshold: number
  is_threshold_met: boolean
}

interface CourseResult {
  course_code: string
  course_title: string
  term_name: string
  result_status: string
  total_marks_obtained: number
  total_marks: number
  percentage: number
  grade?: string
  co_results: COResult[]
}

export function MyResultsClient() {
  const { data, isLoading } = useQuery({
    queryKey: ["student", "results"],
    queryFn: async () => {
      const { data } = await apiClient.GET("/assessment/students/me/results" as never)
      return (data as unknown) as CourseResult[]
    },
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-52 w-full" />)}
      </div>
    )
  }

  if (!data?.length) return <p className="text-muted-foreground text-sm">No published results available yet.</p>

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">My Results</h1>
      {data.map((course) => (
        <Card key={course.course_code}>
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <CardTitle className="text-base">{course.course_title}</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">{course.course_code} · {course.term_name}</p>
              </div>
              <div className="flex items-center gap-2">
                {course.grade && (
                  <Badge variant="outline" className="font-bold">{course.grade}</Badge>
                )}
                <span className="text-sm font-semibold">
                  {course.total_marks_obtained}/{course.total_marks}
                  <span className="text-muted-foreground ml-1 font-normal">({course.percentage.toFixed(1)}%)</span>
                </span>
              </div>
            </div>
          </CardHeader>

          {course.co_results?.length > 0 && (
            <CardContent className="pt-0">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                CO Attainment
              </p>
              <div className="w-full h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={course.co_results} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="co_code" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                    <Tooltip
                      formatter={(value) => [`${Number(value).toFixed(1)}%`, "Attainment"]}
                      contentStyle={{ fontSize: 12 }}
                    />
                    <Bar
                      dataKey="attainment_percentage"
                      fill="var(--color-primary)"
                      radius={[4, 4, 0, 0]}
                    />
                    {course.co_results[0]?.threshold && (
                      <ReferenceLine
                        y={course.co_results[0].threshold}
                        stroke="var(--color-destructive)"
                        strokeDasharray="4 4"
                        label={{ value: "Threshold", fontSize: 10 }}
                      />
                    )}
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {course.co_results.map((co) => (
                  <span
                    key={co.co_code}
                    className={cn(
                      "inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full",
                      co.is_threshold_met
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    )}
                  >
                    {co.co_code} {co.is_threshold_met ? "✓" : "✗"}
                  </span>
                ))}
              </div>
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  )
}
