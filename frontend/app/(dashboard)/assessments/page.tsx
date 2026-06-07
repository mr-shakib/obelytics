import type { Metadata } from "next"
import { AssessmentsClient } from "./assessments-client"

export const metadata: Metadata = { title: "Assessments" }

export default function AssessmentsPage() {
  return <AssessmentsClient />
}
