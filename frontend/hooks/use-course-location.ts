"use client"

import { useQueries, useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Curriculum = { id: string }
type Batch = { id: string; curriculum_id: string }
type CourseSlot = { curriculum_term_definition_id: string; course_id: string }
type ModuleLeaderAssignment = { batch_id: string; course_id: string }

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

  const { data: myModuleAssignments = [] } = useQuery({
    queryKey: queryKeys.moduleLeaderAssignments.mine,
    queryFn: async () => {
      const { data } = await apiClient.GET("/module-leader-assignments/mine" as never)
      return ((data as unknown) as ModuleLeaderAssignment[]) ?? []
    },
    enabled: !!courseId,
  })

  const { data: batches = [] } = useQuery({
    queryKey: queryKeys.batches.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/batches" as never)
      return ((data as unknown) as Batch[]) ?? []
    },
    enabled: !!courseId && myModuleAssignments.some((a) => a.course_id === courseId),
  })

  if (!courseId) return null

  for (let i = 0; i < slotQueries.length; i++) {
    const slot = slotQueries[i].data?.find((s) => s.course_id === courseId)
    if (slot) {
      return { curriculumId: candidates[i].id, termDefId: slot.curriculum_term_definition_id }
    }
  }

  const myAssignment = myModuleAssignments.find((a) => a.course_id === courseId)
  const assignedBatch = myAssignment
    ? batches.find((batch) => batch.id === myAssignment.batch_id)
    : undefined
  if (assignedBatch) return { curriculumId: assignedBatch.curriculum_id, termDefId: "" }

  return null
}
