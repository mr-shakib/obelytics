import type { Metadata } from "next"
import { CoPoMappingClient } from "./co-po-mapping-client"

export const metadata: Metadata = { title: "CO-PO Mappings" }

export default function CoPoMappingPage() {
  return <CoPoMappingClient />
}
