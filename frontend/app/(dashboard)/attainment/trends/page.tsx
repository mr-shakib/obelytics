import type { Metadata } from "next"
import dynamic from "next/dynamic"

const AttainmentTrendsClient = dynamic(() => import("./attainment-trends-client").then(m => m.AttainmentTrendsClient))

export const metadata: Metadata = { title: "Attainment Trends" }

export default function AttainmentTrendsPage() {
  return <AttainmentTrendsClient />
}
