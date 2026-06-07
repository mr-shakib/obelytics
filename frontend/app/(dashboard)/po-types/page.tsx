import type { Metadata } from "next"
import { PoTypesClient } from "./po-types-client"

export const metadata: Metadata = { title: "PO Types" }

export default function PoTypesPage() {
  return <PoTypesClient />
}
