import type { Metadata } from "next"
import { MyCoursesClient } from "./my-courses-client"

export const metadata: Metadata = { title: "My Courses" }

export default function MyCoursesPage() {
  return <MyCoursesClient />
}
