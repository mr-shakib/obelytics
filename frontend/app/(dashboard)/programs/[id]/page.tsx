import type { Metadata } from "next"
import { ProgramDetailClient } from "./program-detail-client"

export const metadata: Metadata = { title: "Program" }

export default async function ProgramPage({ params }: PageProps<"/programs/[id]">) {
  const { id } = await params
  return <ProgramDetailClient id={id} />
}
