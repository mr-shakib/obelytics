import type { Metadata } from "next"
import { DepartmentsClient } from "./departments-client"

export const metadata: Metadata = { title: "Departments" }

export default function DepartmentsPage() {
  return <DepartmentsClient />
}
