import type { Metadata } from "next"
import { connection } from "next/server"

import type { PublicDocs, Visibility } from "@/lib/docs/types"

import { DocsPublicClient, type InitialDocs } from "./docs-public-client"

export const metadata: Metadata = {
  title: "Docs — pitch deck, technical documentation and live system",
  description:
    "Obelytics: AI-native outcome-based education and accreditation. The pitch deck, the technical documentation and a live view of the running system on one page.",
  openGraph: {
    title: "Obelytics Docs",
    description: "Turning academic outcomes into proven capabilities. Pitch deck, technical docs and live system view.",
    type: "website",
  },
}

const BACKEND = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function loadDocs(): Promise<InitialDocs> {
  try {
    const res = await fetch(`${BACKEND}/api/v1/docs/public`, { cache: "no-store" })
    if (res.status === 403) {
      const body = await res.json().catch(() => null)
      return { kind: "unavailable", visibility: (body?.detail ?? null) as Visibility | null }
    }
    if (!res.ok) return { kind: "error" }
    return { kind: "ok", docs: (await res.json()) as PublicDocs }
  } catch {
    return { kind: "error" }
  }
}

export default async function DocsPage() {
  await connection() // rendered per request: visibility and content are live
  return <DocsPublicClient initial={await loadDocs()} />
}
