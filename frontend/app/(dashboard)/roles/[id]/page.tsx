import type { Metadata } from "next"
import { RoleDetailClient } from "./role-detail-client"

export const metadata: Metadata = { title: "Role" }

export default async function RolePage({ params }: PageProps<"/roles/[id]">) {
  const { id } = await params
  return <RoleDetailClient id={id} />
}
