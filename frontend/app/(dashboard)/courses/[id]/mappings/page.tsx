import type { Metadata } from "next"
import { CourseMappingsClient } from "./course-mappings-client"

export const metadata: Metadata = { title: "Outcomes & Mappings" }

export default async function CourseMappingsPage({ params }: PageProps<"/courses/[id]/mappings">) {
  const { id } = await params
  return <CourseMappingsClient id={id} />
}
