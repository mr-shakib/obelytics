import type { Metadata } from "next"
import { SectionOfferingDetailClient } from "./section-offering-detail-client"

export const metadata: Metadata = { title: "Section Offering" }

export default async function SectionOfferingPage({ params }: PageProps<"/section-offerings/[id]">) {
  const { id } = await params
  return <SectionOfferingDetailClient id={id} />
}
