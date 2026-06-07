import type { Metadata } from "next"
import { AuditLogClient } from "./audit-log-client"

export const metadata: Metadata = { title: "Audit Log" }

export default function AuditPage() {
  return <AuditLogClient />
}
