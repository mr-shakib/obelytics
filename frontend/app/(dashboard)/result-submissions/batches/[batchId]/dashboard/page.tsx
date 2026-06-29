import type { Metadata } from "next"
import { BatchPoDashboardClient } from "./batch-po-dashboard-client"

export const metadata: Metadata = { title: "Batch PO Dashboard" }

export default async function BatchPoDashboardPage({ params }: PageProps<"/result-submissions/batches/[batchId]/dashboard">) {
  const { batchId } = await params
  return <BatchPoDashboardClient batchId={batchId} />
}
