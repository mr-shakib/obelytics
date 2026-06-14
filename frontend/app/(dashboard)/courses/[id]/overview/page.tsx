import type { Metadata } from "next"
import { CourseOverviewClient } from "./course-overview-client"

export const metadata: Metadata = { title: "Course Overview" }

export default async function CourseOverviewPage({ params }: PageProps<"/courses/[id]/overview">) {
  const { id } = await params
  return <CourseOverviewClient id={id} />
}
