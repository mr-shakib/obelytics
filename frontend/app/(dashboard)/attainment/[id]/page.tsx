import type { Metadata } from "next"
import dynamic from "next/dynamic"

const AttainmentRunClient = dynamic(() => import("./attainment-run-client").then(m => m.AttainmentRunClient))

export const metadata: Metadata = { title: "Attainment Run" }

export default async function AttainmentRunPage({ params }: PageProps<"/attainment/[id]">) {
  const { id } = await params
  return <AttainmentRunClient id={id} />
}
