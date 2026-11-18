"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ExternalLink, Loader2 } from "lucide-react"
import { useMemo } from "react"
import { toast } from "sonner"

import { DocsView } from "@/components/docs/docs-view"
import { PageHeader } from "@/components/shared/page-header"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { docsAdminApi } from "@/lib/docs/api"
import type { AdminDocs, PublicDocs } from "@/lib/docs/types"
import { cn } from "@/lib/utils"

import { PublishingPanel, STATE_STYLE } from "./publishing-panel"
import { SectionsPanel, type SectionActions } from "./sections-panel"
import { TeamPanel, type TeamActions } from "./team-panel"

const KEY = ["docs", "admin"] as const

/** Drafts shaped like the public page, for the Preview tab. */
function asPreview(docs: AdminDocs): PublicDocs {
  return {
    product: "Obelytics",
    team_name: docs.settings.team_name,
    visibility: docs.visibility,
    team: docs.team,
    generated_at: new Date().toISOString(),
    sections: docs.sections
      .filter((s) => s.is_visible)
      .map((s) => ({
        key: s.key,
        group: s.group,
        kind: s.kind,
        title: s.draft_title,
        body: s.draft_body,
        data: s.draft_data ?? {},
        version: s.published_version + (s.has_changes ? 1 : 0),
        published_at: s.published_at,
      })),
  }
}

export function DocsAdminClient() {
  const qc = useQueryClient()
  const { data: docs, isLoading, isError } = useQuery({ queryKey: KEY, queryFn: docsAdminApi.get, staleTime: 0, refetchOnMount: true })

  const mutation = useMutation({
    mutationFn: ({ run }: { run: () => Promise<AdminDocs>; done?: string }) => run(),
    onSuccess: (data, { done }) => {
      qc.setQueryData(KEY, data)
      void qc.invalidateQueries({ queryKey: ["docs", "public"] })
      if (done) toast.success(done)
    },
  })
  const run = (fn: () => Promise<AdminDocs>, done?: string) => mutation.mutateAsync({ run: fn, done })
  const busy = mutation.isPending

  const sectionActions: SectionActions = {
    busy,
    saveDraft: (id, body) => run(() => docsAdminApi.saveDraft(id, body), "Draft saved"),
    publish: (id) => run(() => docsAdminApi.publish(id), "Published — live on /docs"),
    publishAll: () => run(docsAdminApi.publishAll, "All changes published"),
    discard: (id) => run(() => docsAdminApi.discard(id), "Draft discarded"),
    restore: (id, v) => run(() => docsAdminApi.restore(id, v), `Version ${v} copied into the draft`),
    setVisible: (id, visible) => run(() => docsAdminApi.setVisible(id, visible), visible ? "Section shown" : "Section hidden"),
    remove: (id) => run(() => docsAdminApi.deleteSection(id), "Section deleted"),
    reorder: (ids) => run(() => docsAdminApi.reorderSections(ids)),
    create: (title, group) => run(() => docsAdminApi.createSection(title, group), "Section added"),
  }
  const teamActions: TeamActions = {
    busy,
    add: (form) => run(() => docsAdminApi.addMember(form), "Team member added"),
    update: (id, body) => run(() => docsAdminApi.updateMember(id, body), "Saved"),
    setPhoto: (id, form) => run(() => docsAdminApi.setPhoto(id, form), "Photo updated"),
    deletePhoto: (id) => run(() => docsAdminApi.deletePhoto(id), "Photo removed"),
    remove: (id) => run(() => docsAdminApi.deleteMember(id), "Team member removed"),
    reorder: (ids) => run(() => docsAdminApi.reorderTeam(ids)),
  }

  const preview = useMemo(() => (docs ? asPreview(docs) : null), [docs])

  if (isLoading) return <Loader2 className="mx-auto mt-20 animate-spin text-muted-foreground" />
  if (isError || !docs) {
    return (
      <div className="max-w-xl">
        <PageHeader title="Docs Page" />
        <Alert className="mt-4"><AlertDescription>Only Super Admins can edit the public docs page.</AlertDescription></Alert>
      </div>
    )
  }
  const state = STATE_STYLE[docs.visibility.state]
  const pending = docs.sections.filter((s) => s.has_changes).length

  return (
    <div className="space-y-6">
      <PageHeader
        title="Docs Page"
        description="The public /docs page: pitch deck, technical documentation and live system view. Edit sections, publish them, and control when the page is visible."
        actions={
          <>
            <span className={cn("hidden rounded-full px-2.5 py-1 text-xs font-semibold ring-1 sm:inline-flex", state.className)}>{state.label}</span>
            <Button variant="outline" size="sm" nativeButton={false} render={<a href="/docs" target="_blank" rel="noreferrer" />}>
              Open /docs <ExternalLink data-icon="inline-end" />
            </Button>
          </>
        }
      />
      <Tabs defaultValue="publishing">
        <TabsList>
          <TabsTrigger value="publishing">Publishing</TabsTrigger>
          <TabsTrigger value="sections">Sections{pending ? ` (${pending})` : ""}</TabsTrigger>
          <TabsTrigger value="team">Team ({docs.team.length})</TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
        </TabsList>
        <TabsContent value="publishing" className="pt-4">
          <PublishingPanel
            key={docs.settings.updated_at ?? "settings"}
            docs={docs}
            saving={busy}
            onSave={(body) => void run(() => docsAdminApi.updateSettings(body), "Visibility saved")}
            onReset={() => void run(docsAdminApi.resetWindow, "Back to the default window")}
          />
        </TabsContent>
        <TabsContent value="sections" className="pt-4">
          <SectionsPanel docs={docs} actions={sectionActions} />
        </TabsContent>
        <TabsContent value="team" className="pt-4">
          <TeamPanel docs={docs} actions={teamActions} />
        </TabsContent>
        <TabsContent value="preview" className="pt-4">
          <Alert className="mb-4">
            <AlertDescription>
              Preview of the current drafts, including unpublished changes. Visitors see only published versions.
            </AlertDescription>
          </Alert>
          <div className="overflow-hidden rounded-2xl border">
            {preview && <DocsView docs={preview} mode="preview" />}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
