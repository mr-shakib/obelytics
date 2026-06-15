"use client"

import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import { BookOpen, Users, CalendarDays, Layers, Lock } from "lucide-react"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

type MySection = {
  section_offering_id: string
  course_id: string
  course_code: string
  course_title: string
  batch_id: string
  batch_name: string
  academic_term_id: string
  term_name: string
  term_year: number
  term_season: string
  section_id: string
  section_name: string
  status: string
  result_status: string
  student_count: number
}

export function MySectionsClient() {
  const { data: sections = [], isLoading } = useQuery({
    queryKey: queryKeys.facultyAssignments.mySections,
    queryFn: async () => {
      const { data } = await apiClient.GET("/faculty-assignments/my-sections" as never)
      return ((data as unknown) as MySection[]) ?? []
    },
  })

  return (
    <div className="max-w-5xl space-y-6">
      <PageHeader
        title="My Sections"
        description="Sections where you are the assigned section teacher. Open a section to enter marks and view CO/PO attainment."
      />

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 animate-pulse bg-muted rounded-lg" />
          ))}
        </div>
      ) : sections.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            You are not assigned as section teacher for any section.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {sections.map((section) => {
            const isLocked = section.result_status !== "DRAFT"
            return (
              <Link key={section.section_offering_id} href={`/my-sections/${section.section_offering_id}`}>
                <Card
                  className={cn(
                    "h-full transition-colors hover:border-primary/50 hover:bg-muted/30",
                    isLocked && "border-purple-200 bg-purple-50/50 dark:border-purple-900 dark:bg-purple-950/20"
                  )}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <BookOpen className="h-4 w-4 text-muted-foreground shrink-0" />
                        <div>
                          <p className="font-mono text-sm font-semibold">{section.course_code}</p>
                          <p className="text-sm font-medium">{section.course_title}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={section.status} />
                        {isLocked && <StatusBadge status={section.result_status} />}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <Badge variant="outline" className="gap-1.5 text-xs font-normal">
                        <Layers className="h-3 w-3" />
                        Section {section.section_name}
                      </Badge>
                      <Badge variant="outline" className="gap-1.5 text-xs font-normal">
                        <CalendarDays className="h-3 w-3" />
                        {section.batch_name} &middot; {section.term_name} ({section.term_season} {section.term_year})
                      </Badge>
                      <Badge variant="outline" className="gap-1.5 text-xs font-normal">
                        <Users className="h-3 w-3" />
                        {section.student_count} student{section.student_count === 1 ? "" : "s"}
                      </Badge>
                    </div>
                    {isLocked && (
                      <div className="flex items-center gap-1.5 text-xs font-medium text-purple-700 dark:text-purple-300">
                        <Lock className="h-3 w-3" />
                        Results submitted &mdash; marksheet is locked
                      </div>
                    )}
                  </CardContent>
                </Card>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
