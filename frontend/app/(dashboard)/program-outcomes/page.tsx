import type { Metadata } from "next"
import { ProgramOutcomesClient } from "./program-outcomes-client"

export const metadata: Metadata = { title: "Program Outcomes" }

export default function ProgramOutcomesPage() {
  return <ProgramOutcomesClient />
}
