import type { Metadata } from "next"
import { ResultsClient } from "./results-client"

export const metadata: Metadata = { title: "Results" }

export default async function ResultsPage({ params }: PageProps<"/results/[offering_id]">) {
  const { offering_id } = await params
  return <ResultsClient offeringId={offering_id} />
}
