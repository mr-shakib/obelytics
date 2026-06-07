import type { Metadata } from "next"
import { ProgramOutcomeDetailClient } from "./program-outcome-detail-client"

export const metadata: Metadata = { title: "Program Outcome" }

export default async function ProgramOutcomePage({ params }: PageProps<"/program-outcomes/[id]">) {
  const { id } = await params
  return <ProgramOutcomeDetailClient id={id} />
}
