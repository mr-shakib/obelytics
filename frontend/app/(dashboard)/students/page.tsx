import type { Metadata } from "next"
import { StudentsClient } from "./students-client"

export const metadata: Metadata = { title: "Students" }

export default function StudentsPage() {
  return <StudentsClient />
}
