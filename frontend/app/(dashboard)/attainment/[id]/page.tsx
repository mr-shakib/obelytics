import type { Metadata } from "next"
import { AttainmentRunClient } from "./attainment-run-client"

export const metadata: Metadata = { title: "Attainment Run" }

export default async function AttainmentRunPage({ params }: PageProps<"/attainment/[id]">) {
  const { id } = await params
  return <AttainmentRunClient id={id} />
}
