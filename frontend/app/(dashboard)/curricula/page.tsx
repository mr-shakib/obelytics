import type { Metadata } from "next"
import { CurriculaClient } from "./curricula-client"

export const metadata: Metadata = { title: "Curricula" }

export default function CurriculaPage() {
  return <CurriculaClient />
}
