"use client"

import { ArrowDown, ArrowUp, ImagePlus, Pencil, Plus, Trash2, X } from "lucide-react"
import { useEffect, useState } from "react"

import { TeamAvatar } from "@/components/docs/team-grid"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import type { AdminDocs, TeamMember } from "@/lib/docs/types"

export type TeamActions = {
  busy: boolean
  add: (form: FormData) => Promise<unknown>
  update: (id: string, body: { full_name: string; role: string; email: string }) => Promise<unknown>
  setPhoto: (id: string, form: FormData) => Promise<unknown>
  deletePhoto: (id: string) => Promise<unknown>
  remove: (id: string) => Promise<unknown>
  reorder: (ids: string[]) => Promise<unknown>
}

function usePreview(file: File | null) {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => {
    if (!file) return
    const next = URL.createObjectURL(file)
    // eslint-disable-next-line react-hooks/set-state-in-effect -- object URL must be created and revoked together
    setUrl(next)
    return () => URL.revokeObjectURL(next)
  }, [file])
  return file ? url : null
}

function MemberDialog({ member, open, onOpenChange, actions }: {
  member: TeamMember | null
  open: boolean
  onOpenChange: (o: boolean) => void
  actions: TeamActions
}) {
  const [name, setName] = useState(member?.full_name ?? "")
  const [role, setRole] = useState(member?.role ?? "")
  const [email, setEmail] = useState(member?.email ?? "")
  const [file, setFile] = useState<File | null>(null)
  const preview = usePreview(file)
  const valid = name.trim() && role.trim() && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())

  async function submit() {
    if (!member) {
      const form = new FormData()
      form.set("full_name", name.trim())
      form.set("role", role.trim())
      form.set("email", email.trim())
      if (file) form.set("photo", file)
      await actions.add(form)
    } else {
      await actions.update(member.id, { full_name: name.trim(), role: role.trim(), email: email.trim() })
      if (file) {
        const form = new FormData()
        form.set("photo", file)
        await actions.setPhoto(member.id, form)
      }
    }
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{member ? "Edit team member" : "Add a team member"}</DialogTitle>
          <DialogDescription>Photos are cropped to the same square on the server, so every card matches.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-[140px_minmax(0,1fr)]">
          <div className="space-y-2">
            {preview ? (
              // eslint-disable-next-line @next/next/no-img-element -- local preview of the chosen file
              <img src={preview} alt="" className="aspect-square w-full rounded-2xl object-cover ring-1 ring-border" />
            ) : (
              <TeamAvatar member={{ full_name: name || "?", photo_url: member?.photo_url ?? null }} />
            )}
            <label className="flex cursor-pointer items-center justify-center gap-1.5 rounded-lg border px-2 py-1.5 text-xs font-medium hover:bg-muted">
              <ImagePlus className="size-3.5" aria-hidden /> {file || member?.photo_url ? "Change photo" : "Add photo"}
              <input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </label>
            {member?.photo_url && !file && (
              <Button type="button" variant="ghost" size="xs" className="w-full" onClick={() => void actions.deletePhoto(member.id)}>
                <X data-icon="inline-start" /> Remove photo
              </Button>
            )}
          </div>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="m-name">Full name</Label>
              <Input id="m-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={150} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="m-role">Role in the project</Label>
              <Input id="m-role" value={role} onChange={(e) => setRole(e.target.value)} maxLength={150} placeholder="e.g. Team lead, backend and AI" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="m-email">Email</Label>
              <Input id="m-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} maxLength={255} />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button disabled={!valid || actions.busy} onClick={() => void submit()}>{member ? "Save" : "Add member"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function TeamPanel({ docs, actions }: { docs: AdminDocs; actions: TeamActions }) {
  const [editing, setEditing] = useState<TeamMember | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleting, setDeleting] = useState<TeamMember | null>(null)
  const team = docs.team

  function moveBy(i: number, dir: -1 | 1) {
    const ids = team.map((m) => m.id)
    const j = i + dir
    if (j < 0 || j >= ids.length) return
    ;[ids[i], ids[j]] = [ids[j], ids[i]]
    void actions.reorder(ids)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          Shown in the Team section{docs.settings.team_name ? ` under “${docs.settings.team_name}”` : ""}. Changes are public at once.
        </p>
        <Button size="sm" onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus data-icon="inline-start" /> Add member
        </Button>
      </div>
      {team.length === 0 ? (
        <div className="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground">No team members yet.</div>
      ) : (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
          {team.map((m, i) => (
            <li key={m.id} className="rounded-2xl border bg-card p-3">
              <TeamAvatar member={m} />
              <div className="mt-2 min-w-0">
                <div className="truncate font-semibold">{m.full_name}</div>
                <div className="truncate text-sm text-muted-foreground">{m.role}</div>
                <div className="truncate text-xs text-muted-foreground">{m.email}</div>
              </div>
              <div className="mt-2 flex items-center gap-0.5">
                <Button variant="ghost" size="icon-xs" disabled={i === 0} onClick={() => moveBy(i, -1)} aria-label="Move earlier"><ArrowUp /></Button>
                <Button variant="ghost" size="icon-xs" disabled={i === team.length - 1} onClick={() => moveBy(i, 1)} aria-label="Move later"><ArrowDown /></Button>
                <Button variant="ghost" size="icon-xs" className="ml-auto" onClick={() => { setEditing(m); setDialogOpen(true) }} aria-label={`Edit ${m.full_name}`}><Pencil /></Button>
                <Button variant="ghost" size="icon-xs" onClick={() => setDeleting(m)} aria-label={`Remove ${m.full_name}`}><Trash2 /></Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {dialogOpen && (
        <MemberDialog key={editing?.id ?? "new"} member={editing} open={dialogOpen} onOpenChange={setDialogOpen} actions={actions} />
      )}
      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(o) => !o && setDeleting(null)}
        title={`Remove ${deleting?.full_name ?? "member"}?`}
        description="They are removed from the public Team section."
        confirmLabel="Remove"
        variant="destructive"
        loading={actions.busy}
        onConfirm={() => deleting && void actions.remove(deleting.id).then(() => setDeleting(null))}
      />
    </div>
  )
}
