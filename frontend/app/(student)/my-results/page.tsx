import type { Metadata } from "next"
import { MyResultsClient } from "./my-results-client"

export const metadata: Metadata = { title: "My Results" }

export default function MyResultsPage() {
  return <MyResultsClient />
}
