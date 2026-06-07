import type { Metadata } from "next"
import { CourseDetailClient } from "./course-detail-client"

export const metadata: Metadata = { title: "Course" }

export default async function CoursePage({ params }: PageProps<"/courses/[id]">) {
  const { id } = await params
  return <CourseDetailClient id={id} />
}
