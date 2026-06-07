import type { Metadata } from "next"
import { RefDataClient } from "./ref-data-client"

export const metadata: Metadata = { title: "Reference Data" }

export default function RefDataPage() {
  return <RefDataClient />
}
