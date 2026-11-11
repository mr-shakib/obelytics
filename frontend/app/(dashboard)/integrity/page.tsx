import type { Metadata } from "next"
import { IntegrityClient } from "./integrity-client"

export const metadata: Metadata = { title: "Assessment Integrity" }

export default function IntegrityPage() {
  return <IntegrityClient />
}
