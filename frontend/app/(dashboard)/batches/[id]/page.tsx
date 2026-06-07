import type { Metadata } from "next"
import { BatchDetailClient } from "./batch-detail-client"

export const metadata: Metadata = { title: "Batch" }

export default async function BatchPage({ params }: PageProps<"/batches/[id]">) {
  const { id } = await params
  return <BatchDetailClient id={id} />
}
