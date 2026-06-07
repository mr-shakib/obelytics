import type { Metadata } from "next"
import { CourseOutcomesClient } from "./course-outcomes-client"

export const metadata: Metadata = { title: "Course Outcomes" }

export default function CourseOutcomesPage() {
  return <CourseOutcomesClient />
}
