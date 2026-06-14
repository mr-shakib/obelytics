import type { Metadata } from "next"
import { CourseMaterialsClient } from "./course-materials-client"

export const metadata: Metadata = { title: "Learning Materials" }

export default async function CourseMaterialsPage({ params }: PageProps<"/courses/[id]/materials">) {
  const { id } = await params
  return <CourseMaterialsClient id={id} />
}
