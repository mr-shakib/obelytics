import type { Metadata } from "next"
import { AccreditationClient } from "./accreditation-client"

export const metadata: Metadata = { title: "Accreditation" }

export default function AccreditationPage() {
  return <AccreditationClient />
}
