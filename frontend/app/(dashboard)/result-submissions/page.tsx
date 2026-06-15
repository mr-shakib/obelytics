import type { Metadata } from "next"
import { ResultSubmissionsClient } from "./result-submissions-client"

export const metadata: Metadata = { title: "Result Submissions" }

export default function ResultSubmissionsPage() {
  return <ResultSubmissionsClient />
}
