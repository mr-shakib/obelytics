"use client"

import { useQuery } from "@tanstack/react-query"
import { CoPoMappingCard } from "@/components/courses/co-po-mapping-card"
import { ComplexMappingCard } from "@/components/courses/complex-mapping-card"
import { CoMappingsSummaryCard } from "@/components/courses/co-mappings-summary-card"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { useResolveCourseLocation } from "@/hooks/use-course-location"
import type { CourseOutcome, ProgramOutcome, BloomLevel, CurriculumDetail } from "../course-types"

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

  const { data: curriculumDetail } = useQuery({
    queryKey: queryKeys.curricula.detail(curriculumId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/curricula/${curriculumId}` as never)
      return (data as unknown) as CurriculumDetail
    },
    enabled: !!curriculumId,
  })
  const programId = curriculumDetail?.program_id

  const { data: programOutcomes = [], isFetched: isProgramOutcomesFetched } = useQuery({
    queryKey: queryKeys.programOutcomes.list({ program_id: programId }),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/program-outcomes?program_id=${programId}` as never)
      return ((data as unknown) as ProgramOutcome[]) ?? []
    },
    enabled: !!programId,
  })

  const { data: allProgramOutcomes = [] } = useQuery({
    queryKey: queryKeys.programOutcomes.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/program-outcomes" as never)
      return ((data as unknown) as ProgramOutcome[]) ?? []
    },
    enabled: !!curriculumId && isProgramOutcomesFetched && programOutcomes.length === 0,
  })

  const resolvedPOs = programOutcomes.length > 0 ? programOutcomes : allProgramOutcomes

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
      <CoMappingsSummaryCard
        cos={courseOutcomes}
        pos={resolvedPOs}
        bloomLevels={bloomLevels}
        curriculumId={curriculumId}
        courseId={id}
      />

      <CoPoMappingCard
        curriculumId={curriculumId}
        courseId={id}
        cos={courseOutcomes}
        pos={resolvedPOs}
      />

      <ComplexMappingCard kind="cp" cos={courseOutcomes} />

      <ComplexMappingCard kind="ca" cos={courseOutcomes} />

      <ComplexMappingCard kind="kp" cos={courseOutcomes} />
    </div>
  )
}
