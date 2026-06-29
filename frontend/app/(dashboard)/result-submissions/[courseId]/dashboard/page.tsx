import type { Metadata } from "next"
import { CourseResultDashboardClient } from "./course-result-dashboard-client"

export const metadata: Metadata = { title: "Course Result Dashboard" }

export default async function CourseResultDashboardPage({ params }: PageProps<"/result-submissions/[courseId]/dashboard">) {
  const { courseId } = await params
  return <CourseResultDashboardClient courseId={courseId} />
}
