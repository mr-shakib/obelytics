import type { Metadata } from "next"
import { UserDetailClient } from "./user-detail-client"

export const metadata: Metadata = { title: "User" }

export default async function UserPage({ params }: PageProps<"/users/[id]">) {
  const { id } = await params
  return <UserDetailClient id={id} />
}
