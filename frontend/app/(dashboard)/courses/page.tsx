import type { Metadata } from "next"
import { CoursesClient } from "./courses-client"

export const metadata: Metadata = { title: "Courses" }

export default function CoursesPage() {
  return <CoursesClient />
}
