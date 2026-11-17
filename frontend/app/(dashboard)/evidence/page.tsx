import type { Metadata } from "next"
import { EvidenceClient } from "./evidence-client"

export const metadata: Metadata = { title: "Accreditation Evidence" }

export default function EvidencePage() {
  return <EvidenceClient />
}
