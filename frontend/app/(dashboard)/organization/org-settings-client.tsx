"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

const schema = z.object({
  name: z.string().min(2),
  short_name: z.string().optional(),
  website: z.string().url().optional().or(z.literal("")),
  address_street: z.string().optional(),
})
type FormValues = z.infer<typeof schema>

export function OrgSettingsClient() {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.org.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/organization" as never)
      return (data as unknown) as {
        name: string
        short_name?: string
        website?: string
        address_street?: string
      }
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

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />

  return (
    <div className="max-w-2xl">
      <PageHeader title="Organization" description="Configure your organization settings." />
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
              <Label htmlFor="website">Website</Label>
              <Input id="website" type="url" {...register("website")} placeholder="https://" />
              {errors.website && <p className="text-sm text-destructive">{errors.website.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="address">Address</Label>
              <Input id="address" {...register("address_street")} />
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
