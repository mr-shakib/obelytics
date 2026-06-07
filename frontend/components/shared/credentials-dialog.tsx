"use client"

import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { toast } from "sonner"
import { Copy, Check, Mail, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog"
import { apiClient } from "@/lib/api/client"

export type Credentials = { email: string; full_name: string; password: string }

interface Props {
  creds: Credentials | null
  onClose: () => void
  title?: string
  description?: string
}

export function CredentialsDialog({
  creds,
  onClose,
  title = "Share Credentials",
  description = "The password cannot be retrieved later. Copy or send it to the user now.",
}: Props) {
  const [copied, setCopied] = useState(false)

  const sendEmailMutation = useMutation({
    mutationFn: async () => {
      if (!creds) return
      await apiClient.POST("/users/send-credentials" as never, {
        body: { email: creds.email, full_name: creds.full_name, password: creds.password },
      } as never)
    },
    onSuccess: () => toast.success(`Credentials sent to ${creds?.email}`),
    onError: () => toast.error("Failed to send email — check SMTP settings"),
  })

  function copy() {
    if (!creds) return
    navigator.clipboard.writeText(`Email: ${creds.email}\nPassword: ${creds.password}`)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Dialog open={!!creds} onOpenChange={(o) => { if (!o) { onClose(); setCopied(false) } }}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">{description}</p>
        <div className="rounded-lg border bg-muted/50 p-4 space-y-3 font-mono text-sm">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">Email</p>
            <p className="font-medium break-all">{creds?.email}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">Password</p>
            <p className="font-medium">{creds?.password}</p>
          </div>
        </div>
        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button variant="outline" onClick={copy} className="flex-1 gap-2">
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? "Copied!" : "Copy"}
          </Button>
          <Button
            className="flex-1 gap-2"
            onClick={() => sendEmailMutation.mutate()}
            disabled={sendEmailMutation.isPending}
          >
            {sendEmailMutation.isPending
              ? <Loader2 className="h-4 w-4 animate-spin" />
              : <Mail className="h-4 w-4" />}
            Send Email
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function genPassword() {
  return `Obe-${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`
}
