import type { Metadata } from "next"
import { RolesClient } from "./roles-client"

export const metadata: Metadata = { title: "Roles" }

export default function RolesPage() {
  return <RolesClient />
}
