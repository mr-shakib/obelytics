import type { Metadata } from "next"
import { SectionOfferingsClient } from "./section-offerings-client"

export const metadata: Metadata = { title: "Section Offerings" }

export default function SectionOfferingsPage() {
  return <SectionOfferingsClient />
}
