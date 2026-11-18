"use client"

import { Mail } from "lucide-react"

import { photoSrc } from "@/lib/docs/api"
import type { TeamMember } from "@/lib/docs/types"

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("")
}

/** Uniform cards: every photo is the same square (resized on the server), same frame. */
export function TeamAvatar({ member, className = "" }: { member: Pick<TeamMember, "full_name" | "photo_url">; className?: string }) {
  if (member.photo_url) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- served by the API, already resized
      <img
        src={photoSrc(member.photo_url)}
        alt={member.full_name}
        width={480}
        height={480}
        loading="lazy"
        className={`aspect-square w-full rounded-2xl object-cover ring-1 ring-border ${className}`}
      />
    )
  }
  return (
    <div
      role="img"
      aria-label={member.full_name}
      className={`flex aspect-square w-full items-center justify-center rounded-2xl bg-gradient-to-br from-[#1d7254] to-[#5BD69B] text-4xl font-semibold text-white ring-1 ring-border ${className}`}
    >
      {initials(member.full_name) || "?"}
    </div>
  )
}

export function TeamGrid({ team, teamName, empty }: { team: TeamMember[]; teamName: string | null; empty?: string }) {
  return (
    <div className="space-y-4">
      {teamName && <p className="text-sm font-semibold tracking-wide text-[#1d7254] uppercase dark:text-[#5BD69B]">{teamName}</p>}
      {team.length === 0 ? (
        <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
          {empty ?? "Team profiles are being added."}
        </p>
      ) : (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 print:grid-cols-4">
          {team.map((m) => (
            <li key={m.id} className="flex flex-col rounded-2xl border bg-card p-3 break-inside-avoid">
              <TeamAvatar member={m} />
              <div className="mt-3 min-w-0 px-0.5">
                <div className="truncate font-semibold">{m.full_name}</div>
                <div className="truncate text-sm text-muted-foreground">{m.role}</div>
                <a
                  href={`mailto:${m.email}`}
                  className="mt-1.5 inline-flex max-w-full items-center gap-1 truncate text-xs text-[#1d7254] hover:underline dark:text-[#5BD69B]"
                >
                  <Mail className="size-3 shrink-0" aria-hidden />
                  <span className="truncate">{m.email}</span>
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
