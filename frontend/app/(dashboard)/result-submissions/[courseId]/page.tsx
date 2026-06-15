import type { Metadata } from "next"
import { CourseResultSubmissionsClient } from "./course-result-submissions-client"

export const metadata: Metadata = { title: "Result Submissions" }

export default async function CourseResultSubmissionsPage({ params }: PageProps<"/result-submissions/[courseId]">) {
  const { courseId } = await params
  return <CourseResultSubmissionsClient courseId={courseId} />
}
