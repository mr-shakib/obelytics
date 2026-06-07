import type { Metadata } from "next"
import { DepartmentDetailClient } from "./department-detail-client"

export const metadata: Metadata = { title: "Department" }

export default async function DepartmentPage({ params }: PageProps<"/departments/[id]">) {
  const { id } = await params
  return <DepartmentDetailClient id={id} />
}
