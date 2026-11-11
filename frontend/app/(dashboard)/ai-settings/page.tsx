import type { Metadata } from "next"
import { AISettingsClient } from "./ai-settings-client"

export const metadata: Metadata = { title: "AI Settings" }

export default function AISettingsPage() {
  return <AISettingsClient />
}
