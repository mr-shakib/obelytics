"use client"

import { useQuery } from "@tanstack/react-query"
import { CoPoMappingCard } from "@/components/courses/co-po-mapping-card"
import { ComplexMappingCard } from "@/components/courses/complex-mapping-card"
import { CoMappingsSummaryCard } from "@/components/courses/co-mappings-summary-card"
import { AddCourseOutcomeDialog } from "@/components/courses/add-course-outcome-dialog"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { useResolveCourseLocation } from "@/hooks/use-course-location"
import type { CourseOutcome, ProgramOutcome, BloomLevel } from "../course-types"

interface Props {
  id: string
}

export function CourseMappingsClient({ id }: Props) {
  const courseLocation = useResolveCourseLocation(id)
  const curriculumId = courseLocation?.curriculumId

  const { data: courseOutcomes = [] } = useQuery({
    queryKey: queryKeys.courseOutcomes.list(curriculumId, id),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/course-outcomes?curriculum_id=${curriculumId}&course_id=${id}` as never
      )
      return ((data as unknown) as CourseOutcome[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: programOutcomes = [] } = useQuery({
    queryKey: queryKeys.programOutcomes.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/program-outcomes" as never)
      return ((data as unknown) as ProgramOutcome[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: bloomLevels = [] } = useQuery({
    queryKey: queryKeys.refData.bloomLevels,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-levels" as never)
      return ((data as unknown) as BloomLevel[]) ?? []
    },
  })

  if (!curriculumId) {
    return (
      <p className="text-sm text-muted-foreground">
        This course is not part of any curriculum yet.
      </p>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <AddCourseOutcomeDialog
          curriculumId={curriculumId}
          courseId={id}
          nextOutcomeNumber={courseOutcomes.length + 1}
        />
      </div>

      <CoMappingsSummaryCard
        cos={courseOutcomes}
        pos={programOutcomes}
        bloomLevels={bloomLevels}
        curriculumId={curriculumId}
        courseId={id}
      />

      <CoPoMappingCard
        curriculumId={curriculumId}
        courseId={id}
        cos={courseOutcomes}
        pos={programOutcomes}
      />

      <ComplexMappingCard kind="cp" cos={courseOutcomes} />

      <ComplexMappingCard kind="ca" cos={courseOutcomes} />

      <ComplexMappingCard kind="kp" cos={courseOutcomes} />
    </div>
  )
}
