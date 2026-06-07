import type { Metadata } from "next"
import { ApprovalsClient } from "./approvals-client"

export const metadata: Metadata = { title: "Approvals" }

export default function ApprovalsPage() {
  return <ApprovalsClient />
}
