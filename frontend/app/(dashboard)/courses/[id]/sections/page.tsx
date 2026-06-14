import type { Metadata } from "next"
import { CourseSectionsClient } from "./course-sections-client"

export const metadata: Metadata = { title: "Sections" }

export default async function CourseSectionsPage({ params }: PageProps<"/courses/[id]/sections">) {
  const { id } = await params
  return <CourseSectionsClient courseId={id} />
}
