import type { Metadata } from "next"
import dynamic from "next/dynamic"

const MyResultsClient = dynamic(() => import("./my-results-client").then(m => m.MyResultsClient))

export const metadata: Metadata = { title: "My Results" }

export default function MyResultsPage() {
  return <MyResultsClient />
}
