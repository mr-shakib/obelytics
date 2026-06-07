import type { Metadata } from "next"
import { CoMappingsClient } from "./co-mappings-client"

export const metadata: Metadata = { title: "CO Mappings" }

export default async function CoMappingsPage({ params }: PageProps<"/course-outcomes/[id]/mappings">) {
  const { id } = await params
  return <CoMappingsClient coId={id} />
}
