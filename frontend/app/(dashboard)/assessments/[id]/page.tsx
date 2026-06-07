import type { Metadata } from "next"
import { AssessmentDetailClient } from "./assessment-detail-client"

export const metadata: Metadata = { title: "Assessment" }

export default async function AssessmentPage({ params }: PageProps<"/assessments/[id]">) {
  const { id } = await params
  return <AssessmentDetailClient id={id} />
}
