import type { Metadata } from "next"
import { CopilotClient } from "./copilot-client"

export const metadata: Metadata = { title: "OBE Copilot" }

export default function CopilotPage() {
  return <CopilotClient />
}
