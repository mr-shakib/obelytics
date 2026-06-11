import type { Metadata } from "next"
import { ModuleLeadersClient } from "./module-leaders-client"

export const metadata: Metadata = { title: "Module Leaders" }

export default function ModuleLeadersPage() {
  return <ModuleLeadersClient />
}
