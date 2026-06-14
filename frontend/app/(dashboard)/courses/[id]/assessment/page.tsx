import type { Metadata } from "next"
import { CourseAssessmentClient } from "./course-assessment-client"

export const metadata: Metadata = { title: "Assessment" }

export default async function CourseAssessmentPage({ params }: PageProps<"/courses/[id]/assessment">) {
  const { id } = await params
  return <CourseAssessmentClient id={id} />
}
