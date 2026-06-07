import type { Metadata } from "next"
import { CurriculumDetailClient } from "./curriculum-detail-client"

export const metadata: Metadata = { title: "Curriculum" }

export default async function CurriculumPage({ params }: PageProps<"/curricula/[id]">) {
  const { id } = await params
  return <CurriculumDetailClient id={id} />
}
