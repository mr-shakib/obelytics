import type { Metadata } from "next"
import { AccreditationCycleClient } from "./accreditation-cycle-client"

export const metadata: Metadata = { title: "Accreditation Cycle" }

export default async function AccreditationCyclePage({ params }: PageProps<"/accreditation/[cycle_id]">) {
  const { cycle_id } = await params
  return <AccreditationCycleClient cycleId={cycle_id} />
}
