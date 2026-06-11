"use client"

import { useQueries, useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Curriculum = { id: string }
type CourseSlot = { curriculum_term_definition_id: string; course_id: string }

/**
 * Resolves which curriculum and term a course belongs to, by scanning the
 * course-slots of every curriculum. Used to deep-link into the Course
 * Outcomes / CO-PO Mapping pages from a `?course_id=` query param.
 */
export function useResolveCourseLocation(courseId: string) {
  const { data: curricula = [] } = useQuery({
    queryKey: queryKeys.curricula.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/curricula" as never)
      return ((data as unknown) as Curriculum[]) ?? []
    },
    enabled: !!courseId,
  })

  const candidates = courseId ? curricula : []

  const slotQueries = useQueries({
    queries: candidates.map((c) => ({
      queryKey: queryKeys.curricula.courseSlots(c.id),
      queryFn: async () => {
        const { data } = await apiClient.GET(`/curricula/${c.id}/course-slots` as never)
        return ((data as unknown) as CourseSlot[]) ?? []
      },
    })),
  })

  if (!courseId) return null

  for (let i = 0; i < slotQueries.length; i++) {
    const slot = slotQueries[i].data?.find((s) => s.course_id === courseId)
    if (slot) {
      return { curriculumId: candidates[i].id, termDefId: slot.curriculum_term_definition_id }
    }
  }
  return null
}
