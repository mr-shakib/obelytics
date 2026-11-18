"use client"

import { useQuery } from "@tanstack/react-query"

import { DocsUnavailable } from "@/components/docs/docs-unavailable"
import { DocsView } from "@/components/docs/docs-view"
import { DocsUnavailableError, docsPublicApi } from "@/lib/docs/api"
import type { PublicDocs, Visibility } from "@/lib/docs/types"

export type InitialDocs =
  | { kind: "ok"; docs: PublicDocs }
  | { kind: "unavailable"; visibility: Visibility | null }
  | { kind: "error" }

type State = { docs: PublicDocs | null; visibility: Visibility | null }

async function load(): Promise<State> {
  try {
    return { docs: await docsPublicApi.docs(), visibility: null }
  } catch (err) {
    if (err instanceof DocsUnavailableError) return { docs: null, visibility: err.visibility }
    throw err
  }
}

/** Keeps the server-rendered page current: published edits and schedule changes show up within a minute. */
export function DocsPublicClient({ initial }: { initial: InitialDocs }) {
  const { data, isError } = useQuery<State>({
    queryKey: ["docs", "public"],
    queryFn: load,
    initialData:
      initial.kind === "ok"
        ? { docs: initial.docs, visibility: null }
        : initial.kind === "unavailable"
          ? { docs: null, visibility: initial.visibility }
          : undefined,
    staleTime: 20_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })

  if (data?.docs) return <DocsView docs={data.docs} mode="public" />
  if (data && !data.docs) return <DocsUnavailable visibility={data.visibility} />
  if (isError || initial.kind === "error") return <DocsUnavailable visibility={null} />
  return null
}
