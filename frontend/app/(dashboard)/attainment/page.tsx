import type { Metadata } from "next"
import { AttainmentClient } from "./attainment-client"

export const metadata: Metadata = { title: "Attainment" }

export default function AttainmentPage() {
  return <AttainmentClient />
}
