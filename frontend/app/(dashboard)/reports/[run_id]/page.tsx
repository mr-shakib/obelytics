import type { Metadata } from "next"
import { ReportRunClient } from "./report-run-client"

export const metadata: Metadata = { title: "Report Run" }

export default async function ReportRunPage({ params }: PageProps<"/reports/[run_id]">) {
  const { run_id } = await params
  return <ReportRunClient runId={run_id} />
}
