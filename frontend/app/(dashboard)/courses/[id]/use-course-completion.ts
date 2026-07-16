"use client"

import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { useResolveCourseLocation } from "@/hooks/use-course-location"
import type { Course, CourseAssessmentTool } from "./course-types"

export const REQUIRED_DELIVERY_PLAN_WEEKS = 12

export interface CompletionCheck {
  label: string
  done: boolean
}

// Course design completion — the same checklist gates both the outline PDF
// download and section creation: a course must be 100% designed first.
export function useCourseCompletion(courseId: string) {
  const courseLocation = useResolveCourseLocation(courseId)
  const curriculumId = courseLocation?.curriculumId

  const { data: course, isLoading: isCourseLoading } = useQuery({
    queryKey: queryKeys.courses.detail(courseId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/courses/${courseId}` as never)
      return (data as unknown) as Course
    },
  })

  const { data: courseOutcomes = [] } = useQuery({
    queryKey: queryKeys.courseOutcomes.list(curriculumId, courseId),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/course-outcomes?curriculum_id=${curriculumId}&course_id=${courseId}` as never
      )
      return ((data as unknown) as { id: string }[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: objectives = [] } = useQuery({
    queryKey: queryKeys.courseObjectives.byCourse(courseId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/courses/${courseId}/objectives` as never)
      return ((data as unknown) as { statement: string }[]) ?? []
    },
  })

  const { data: lessonPlan = [] } = useQuery({
    queryKey: queryKeys.courseLessonPlan.byCourse(courseId, curriculumId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/courses/${courseId}/lesson-plan?curriculum_id=${curriculumId}` as never
      )
      return ((data as unknown) as { id: string; week_number: number }[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: mappingSet } = useQuery({
    queryKey: queryKeys.coPoMappings.byCourse(curriculumId ?? "", courseId),
    queryFn: async () => {
      try {
        const { data } = await apiClient.GET(
          `/mappings/co-po?curriculum_id=${curriculumId}&course_id=${courseId}` as never
        ) as { data: unknown }
        return ((data as unknown) as { id: string } | null) ?? null
      } catch {
        return null
      }
    },
    enabled: !!curriculumId,
    retry: false,
  })

  const { data: assessmentTools = [] } = useQuery({
    queryKey: queryKeys.courseAssessmentTools.byCourse(courseId, curriculumId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/courses/${courseId}/assessment-tools?curriculum_id=${curriculumId}` as never
      )
      return ((data as unknown) as CourseAssessmentTool[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const checks: CompletionCheck[] = []
  checks.push({ label: "Course description", done: !!course?.description })
  checks.push({ label: "Course objectives", done: objectives.length > 0 })
  checks.push({ label: "Course outcomes (COs)", done: courseOutcomes.length > 0 })
  checks.push({ label: "Assessment tools", done: assessmentTools.length > 0 })
  checks.push({ label: "CO-PO mapping", done: !!mappingSet })
  // Complete once every week from 1 through the required minimum is covered —
  // a longer plan (13+ weeks) still counts, it just can't have gaps in 1..12.
  const plannedWeekSet = new Set(lessonPlan.map((item) => item.week_number))
  const hasCompleteDeliveryPlan = Array.from(
    { length: REQUIRED_DELIVERY_PLAN_WEEKS },
    (_, i) => i + 1
  ).every((week) => plannedWeekSet.has(week))
  checks.push({ label: "Delivery plan", done: hasCompleteDeliveryPlan })

  const completedCount = checks.filter((c) => c.done).length
  const completionPct = Math.round((completedCount / checks.length) * 100)
  const isComplete = completionPct === 100

  return {
    course,
    isCourseLoading,
    curriculumId,
    assessmentTools,
    checks,
    completedCount,
    completionPct,
    isComplete,
  }
}
