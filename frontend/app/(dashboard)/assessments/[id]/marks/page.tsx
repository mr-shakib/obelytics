import type { Metadata } from "next"
import { MarksEntryClient } from "./marks-entry-client"

export const metadata: Metadata = { title: "Marks Entry" }

export default async function MarksPage({ params }: PageProps<"/assessments/[id]/marks">) {
  const { id } = await params
  return <MarksEntryClient assessmentId={id} />
}
