import type { Metadata } from "next"
import { OrgSettingsClient } from "./org-settings-client"

export const metadata: Metadata = { title: "Organization" }

export default function OrganizationPage() {
  return <OrgSettingsClient />
}
