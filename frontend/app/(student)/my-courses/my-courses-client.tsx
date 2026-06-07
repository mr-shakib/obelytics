"use client"

import { useQuery } from "@tanstack/react-query"
import { Users, ClipboardList } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { StatusBadge } from "@/components/shared/status-badge"
import { apiClient } from "@/lib/api/client"
import { formatDate } from "@/lib/utils"

interface Enrollment {
  id: string
  course_code: string
  course_title: string
  credits: number
  section: string
  faculty_name: string
  term_name: string
  status: string
  assessments: { title: string; type: string; total_marks: number; weightage: number }[]
}

export function MyCoursesClient() {
  const { data, isLoading } = useQuery({
    queryKey: ["student", "courses"],
    queryFn: async () => {
      const { data } = await apiClient.GET("/assessment/students/me/enrollments" as never)
      return (data as unknown) as Enrollment[]
    },
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-40 w-full" />)}
      </div>
    )
  }

  if (!data?.length) return <p className="text-muted-foreground text-sm">No active enrollments.</p>

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">My Courses</h1>
      {data.map((enrollment) => (
        <Card key={enrollment.id}>
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <CardTitle className="text-base">{enrollment.course_title}</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {enrollment.course_code} · {enrollment.credits} credits · Section {enrollment.section}
                </p>
              </div>
              <StatusBadge status={enrollment.status} />
            </div>
            <div className="flex items-center gap-4 text-xs text-muted-foreground mt-2">
              <span className="flex items-center gap-1"><Users className="h-3 w-3" />{enrollment.faculty_name}</span>
              <span>{enrollment.term_name}</span>
            </div>
          </CardHeader>
          {enrollment.assessments?.length > 0 && (
            <CardContent className="pt-0">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1">
                <ClipboardList className="h-3 w-3" /> Assessments
              </p>
              <div className="flex flex-wrap gap-2">
                {enrollment.assessments.map((a, i) => (
                  <div key={i} className="border rounded-md px-2 py-1 text-xs">
                    <span className="font-medium">{a.title}</span>
                    <span className="text-muted-foreground ml-1">/{a.total_marks} ({a.weightage}%)</span>
                  </div>
                ))}
              </div>
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  )
}
