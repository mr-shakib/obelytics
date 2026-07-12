"use client"

import { useRef, useState } from "react"
import { toast } from "sonner"
import { Download, DatabaseBackup, Loader2 } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { PageHeader } from "@/components/shared/page-header"
import { useAuthStore } from "@/lib/stores/auth-store"

function IndeterminateBar() {
  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
      <div className="h-full w-1/3 rounded-full bg-primary animate-[indeterminate-bar_1.4s_ease-in-out_infinite]" />
    </div>
  )
}

export function SystemSettingsClient() {
  const { accessToken } = useAuthStore()
  const restoreInputRef = useRef<HTMLInputElement>(null)
  const [isRestoring, setIsRestoring] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const busy = isRestoring || isDownloading

  async function handleBackupDownload() {
    setIsDownloading(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/admin/backup`, {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      })
      if (!res.ok) throw new Error("backup_failed")
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      const cd = res.headers.get("Content-Disposition") ?? ""
      const match = cd.match(/filename=(.+)/)
      a.download = match ? match[1] : "obelytics_backup.json"
      a.click()
      URL.revokeObjectURL(url)
      toast.success("Backup downloaded")
    } catch {
      toast.error("Failed to download backup")
    } finally {
      setIsDownloading(false)
    }
  }

  async function handleRestoreFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ""

    if (!window.confirm(
      "Restoring a backup will replace ALL current data with the contents of the backup file.\n\nAnything not saved in the backup will be permanently lost.\n\nDo you want to continue?"
    )) return

    setIsRestoring(true)
    try {
      const form = new FormData()
      form.append("file", file)
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/admin/restore`, {
        method: "POST",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        body: form,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail ?? "Restore failed")
      }
      toast.success("Database restored. Please refresh the page.")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Restore failed")
    } finally {
      setIsRestoring(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <PageHeader title="System Settings" description="Super admin controls for data management." />

      <Card>
        <CardHeader>
          <CardTitle>Backup &amp; Restore</CardTitle>
          <CardDescription>
            Save a copy of all your data to keep it safe, or load a previously saved backup to
            bring the system back to an earlier state. The backup file contains all users,
            curricula, assessments, OBE data, and permission settings.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border p-4 space-y-3">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-medium text-sm">Create a Backup</p>
                <p className="text-sm text-muted-foreground mt-0.5">
                  Download a backup file of everything in the system right now. Keep this file somewhere safe — you can use it to restore the system later.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                className="shrink-0"
                disabled={busy}
                onClick={handleBackupDownload}
              >
                {isDownloading ? <Loader2 className="animate-spin" /> : <Download />}
                {isDownloading ? "Preparing Backup…" : "Download Backup"}
              </Button>
            </div>
            {isDownloading && (
              <div className="space-y-1">
                <IndeterminateBar />
                <p className="text-xs text-muted-foreground">Gathering all data into a backup file — this may take a moment…</p>
              </div>
            )}
          </div>

          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 space-y-3">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-medium text-sm">Restore from a Backup</p>
                <p className="text-sm text-muted-foreground mt-0.5">
                  Upload a backup file to replace all current data with a saved version.
                  <span className="font-medium text-destructive"> This will permanently erase everything that is not in the backup file.</span>
                </p>
              </div>
              <input
                ref={restoreInputRef}
                type="file"
                accept="application/json,.json"
                className="hidden"
                onChange={handleRestoreFile}
              />
              <Button
                type="button"
                variant="destructive"
                className="shrink-0"
                disabled={busy}
                onClick={() => restoreInputRef.current?.click()}
              >
                {isRestoring ? <Loader2 className="animate-spin" /> : <DatabaseBackup />}
                {isRestoring ? "Restoring…" : "Restore Backup"}
              </Button>
            </div>
            {isRestoring && (
              <div className="space-y-1">
                <IndeterminateBar />
                <p className="text-xs text-muted-foreground">Restoring all data from the backup file — please don&apos;t close this page…</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
