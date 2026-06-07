import type { Metadata } from "next"
import { AttainmentTrendsClient } from "./attainment-trends-client"

export const metadata: Metadata = { title: "Attainment Trends" }

export default function AttainmentTrendsPage() {
  return <AttainmentTrendsClient />
}
