import type { Metadata } from "next"
import { MyCurriculumClient } from "./my-curriculum-client"

export const metadata: Metadata = { title: "My Curriculum" }

export default function MyCurriculumPage() {
  return <MyCurriculumClient />
}
