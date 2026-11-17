import type { Metadata } from "next"
import { WorkforceClient } from "./workforce-client"

export const metadata: Metadata = { title: "Workforce Readiness" }

export default function WorkforcePage() {
  return <WorkforceClient />
}
