import type { Metadata } from "next"
import { MarksheetClient } from "./marksheet-client"

export const metadata: Metadata = { title: "Marksheet" }

export default async function MarksheetPage({ params }: PageProps<"/my-sections/[id]">) {
  const { id } = await params
  return <MarksheetClient sectionOfferingId={id} />
}
