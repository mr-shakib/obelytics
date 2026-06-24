import type { Metadata } from "next"
import { POVersionDetailClient } from "./po-version-detail-client"

export const metadata: Metadata = { title: "PO Version" }

export default async function POVersionPage({ params }: PageProps<"/program-outcomes/[id]">) {
  const { id } = await params
  return <POVersionDetailClient versionId={id} />
}
