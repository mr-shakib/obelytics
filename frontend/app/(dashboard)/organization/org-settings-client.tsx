"use client"

import { useRef, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, Building2, Upload } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { useAuthStore } from "@/lib/stores/auth-store"

const schema = z.object({
  name: z.string().min(2),
  short_name: z.string().optional(),
  description: z.string().optional(),
  vision: z.string().optional(),
  mission: z.string().optional(),
  website: z.string().url().optional().or(z.literal("")),
})
type FormValues = z.infer<typeof schema>

type OrgData = FormValues & { logo_url?: string | null }

export function OrgSettingsClient() {
  const qc = useQueryClient()
  const { accessToken } = useAuthStore()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoPreview, setLogoPreview] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.org.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/organization" as never)
      return (data as unknown) as OrgData
    },
  })

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: data,
  })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.PATCH("/organization" as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Organization settings saved")
      qc.invalidateQueries({ queryKey: queryKeys.org.all })
    },
    onError: () => toast.error("Failed to save settings"),
  })

  const logoMutation = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData()
      form.append("file", file)
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/organization/logo`, {
        method: "POST",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        body: form,
      })
      if (!res.ok) throw new Error("upload_failed")
      return res.json()
    },
    onSuccess: () => {
      toast.success("Logo updated")
      qc.invalidateQueries({ queryKey: queryKeys.org.all })
      setLogoFile(null)
      setLogoPreview(null)
    },
    onError: () => toast.error("Failed to upload logo"),
  })

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setLogoFile(file)
    setLogoPreview(URL.createObjectURL(file))
  }

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />

  const displayLogo = logoPreview ?? data?.logo_url ?? null

  return (
    <div className="max-w-2xl space-y-6">
      <PageHeader title="Organization" description="Configure your organization settings." />

      <Card>
        <CardHeader><CardTitle>Logo</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex size-20 shrink-0 items-center justify-center overflow-hidden rounded-xl border bg-muted">
              {displayLogo ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={displayLogo} alt="Organization logo" className="size-full object-contain" />
              ) : (
                <Building2 className="size-8 text-muted-foreground" />
              )}
            </div>
            <div className="space-y-2">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFileChange}
              />
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
                  <Upload />
                  Choose image
                </Button>
                <PermissionGate permission="system.organization.configure">
                  <Button
                    type="button"
                    disabled={!logoFile || logoMutation.isPending}
                    onClick={() => logoFile && logoMutation.mutate(logoFile)}
                  >
                    {logoMutation.isPending && <Loader2 className="animate-spin" />}
                    Upload
                  </Button>
                </PermissionGate>
              </div>
              <p className="text-xs text-muted-foreground">PNG, JPG or SVG. Max 2MB.</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Details</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Organization Name</Label>
              <Input id="name" {...register("name")} />
              {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="short_name">Short Name / Acronym</Label>
              <Input id="short_name" {...register("short_name")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea id="description" rows={3} {...register("description")} placeholder="A brief description of the institution..." />
            </div>
            <div className="space-y-2">
              <Label htmlFor="vision">Vision</Label>
              <Textarea id="vision" rows={3} {...register("vision")} placeholder="The institution's vision statement..." />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mission">Mission</Label>
              <Textarea id="mission" rows={3} {...register("mission")} placeholder="The institution's mission statement..." />
            </div>
            <div className="space-y-2">
              <Label htmlFor="website">Website</Label>
              <Input id="website" type="url" {...register("website")} placeholder="https://" />
              {errors.website && <p className="text-sm text-destructive">{errors.website.message}</p>}
            </div>
            <PermissionGate permission="system.organization.configure">
              <Button type="submit" disabled={isSubmitting || mutation.isPending}>
                {(isSubmitting || mutation.isPending) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save Changes
              </Button>
            </PermissionGate>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
