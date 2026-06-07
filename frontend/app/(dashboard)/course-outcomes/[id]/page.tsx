import type { Metadata } from "next"
import { CourseOutcomeDetailClient } from "./course-outcome-detail-client"

export const metadata: Metadata = { title: "Course Outcome" }

export default async function CourseOutcomePage({ params }: PageProps<"/course-outcomes/[id]">) {
  const { id } = await params
  return <CourseOutcomeDetailClient id={id} />
}
