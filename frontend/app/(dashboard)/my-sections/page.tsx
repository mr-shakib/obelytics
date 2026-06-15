import type { Metadata } from "next"
import { MySectionsClient } from "./my-sections-client"

export const metadata: Metadata = { title: "My Sections" }

export default function MySectionsPage() {
  return <MySectionsClient />
}
