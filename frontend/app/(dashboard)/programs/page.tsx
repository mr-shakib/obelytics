import type { Metadata } from "next"
import { ProgramsClient } from "./programs-client"

export const metadata: Metadata = { title: "Programs" }

export default function ProgramsPage() {
  return <ProgramsClient />
}
