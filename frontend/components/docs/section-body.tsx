"use client"

import { ExternalLink, PlayCircle } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { ChangelogItem, DocsMode, DocsSection, FeatureItem, PublicDocs } from "@/lib/docs/types"

import { AnalyticsPanel, ApiPanel, ChangelogTimeline, FeatureMatrix, UsageTable } from "./live"
import { Markdown } from "./markdown"
import { MermaidDiagram } from "./mermaid-diagram"
import { TeamGrid } from "./team-grid"

type Props = { section: DocsSection; docs: PublicDocs; mode: DocsMode }

/** youtu.be/ID, youtube.com/watch?v=ID, /shorts/ID or /embed/ID → privacy-enhanced embed URL. */
export function youtubeEmbed(url: string | undefined): string | null {
  if (!url) return null
  const m = url.match(/(?:youtu\.be\/|youtube(?:-nocookie)?\.com\/(?:watch\?(?:.*&)?v=|shorts\/|embed\/|live\/))([\w-]{11})/)
  return m ? `https://www.youtube-nocookie.com/embed/${m[1]}?rel=0` : null
}

function Demo({ section }: Props) {
  const embed = youtubeEmbed(section.data.video_url)
  return (
    <div className="space-y-5">
      {embed && (
        <div className="overflow-hidden rounded-2xl border bg-black shadow-sm print:hidden">
          <iframe
            src={embed}
            title="Obelytics demo video"
            className="aspect-video w-full"
            loading="lazy"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            referrerPolicy="strict-origin-when-cross-origin"
            allowFullScreen
          />
        </div>
      )}
      {section.data.video_url && (
        <p className="hidden text-sm print:block">Video: {section.data.video_url}</p>
      )}
      <Markdown>{section.body}</Markdown>
      <div className="flex flex-wrap gap-2 print:hidden">
        {section.data.demo_url && (
          <Button nativeButton={false} render={<a href={section.data.demo_url} target="_blank" rel="noreferrer" />}>
            Open the live demo <ExternalLink data-icon="inline-end" />
          </Button>
        )}
        {section.data.video_url && !embed && (
          <Button variant="outline" nativeButton={false} render={<a href={section.data.video_url} target="_blank" rel="noreferrer" />}>
            <PlayCircle data-icon="inline-start" /> Watch the video
          </Button>
        )}
      </div>
    </div>
  )
}

const RENDERERS: Record<string, (props: Props) => React.ReactNode> = {
  markdown: ({ section }) => <Markdown>{section.body}</Markdown>,
  contributors: ({ section }) => <Markdown>{section.body}</Markdown>,
  demo: Demo,
  traction: ({ section, mode }) => (
    <div className="space-y-5">
      <Markdown>{section.body}</Markdown>
      <UsageTable mode={mode} />
    </div>
  ),
  features: ({ section, mode }) => (
    <div className="space-y-4">
      <Markdown>{section.body}</Markdown>
      <FeatureMatrix items={(section.data.items ?? []) as FeatureItem[]} mode={mode} />
    </div>
  ),
  diagram: ({ section }) => (
    <div className="space-y-4">
      <Markdown>{section.body}</Markdown>
      <MermaidDiagram code={section.data.mermaid ?? ""} label={section.title} />
    </div>
  ),
  api: ({ section, mode }) => (
    <div className="space-y-5">
      <Markdown>{section.body}</Markdown>
      <ApiPanel mode={mode} />
    </div>
  ),
  analytics: ({ section, mode }) => (
    <div className="space-y-5">
      <Markdown>{section.body}</Markdown>
      <AnalyticsPanel mode={mode} />
    </div>
  ),
  team: ({ section, docs }) => (
    <div className="space-y-4">
      <Markdown>{section.body}</Markdown>
      <TeamGrid team={docs.team} teamName={docs.team_name} />
    </div>
  ),
  changelog: ({ section }) => (
    <div className="space-y-5">
      <Markdown>{section.body}</Markdown>
      <ChangelogTimeline items={(section.data.items ?? []) as ChangelogItem[]} />
    </div>
  ),
}

/**
 * Renders a section by its kind. To add a kind: give the backend a default and data rules
 * (live_docs/defaults.py, service.clean_data) and add a renderer here.
 */
export function SectionBody(props: Props) {
  const render = RENDERERS[props.section.kind] ?? RENDERERS.markdown
  return <>{render(props)}</>
}
