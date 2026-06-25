"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2 } from "lucide-react"
import { useState } from "react"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type BloomDomain = { id: string; name: string; level: number; description?: string }
type AssessmentType = { id: string; name: string; description?: string }

const bdSchema = z.object({
  name: z.string().min(1, "Name required"),
  level: z.number().int().min(1).max(6),
  description: z.string().optional(),
})
type BDForm = z.infer<typeof bdSchema>

const atSchema = z.object({
  name: z.string().min(1, "Name required"),
  description: z.string().optional(),
})
type ATForm = z.infer<typeof atSchema>

export function RefDataClient() {
  const qc = useQueryClient()
  const [bdOpen, setBdOpen] = useState(false)
  const [atOpen, setAtOpen] = useState(false)

  const { data: bloomDomains = [], isLoading: bdLoading } = useQuery({
    queryKey: queryKeys.refData.bloomDomains,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-domains" as never)
      return ((data as unknown) as { items?: BloomDomain[] })?.items ?? ((data as unknown) as BloomDomain[]) ?? []
    },
  })

  const { data: assessmentTypes = [], isLoading: atLoading } = useQuery({
    queryKey: queryKeys.refData.assessmentTypes,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/assessment-types" as never)
      return ((data as unknown) as { items?: AssessmentType[] })?.items ?? ((data as unknown) as AssessmentType[]) ?? []
    },
  })

  const bdForm = useForm<BDForm>({ resolver: zodResolver(bdSchema) })
  const atForm = useForm<ATForm>({ resolver: zodResolver(atSchema) })

  const bdMutation = useMutation({
    mutationFn: async (v: BDForm) => {
      await apiClient.POST("/ref-data/bloom-domains" as never, { body: v } as never)
    },
    onSuccess: () => {
      toast.success("Bloom domain created")
      qc.invalidateQueries({ queryKey: queryKeys.refData.bloomDomains })
      bdForm.reset()
      setBdOpen(false)
    },
    onError: () => toast.error("Failed to create bloom domain"),
  })

  const atMutation = useMutation({
    mutationFn: async (v: ATForm) => {
      await apiClient.POST("/ref-data/assessment-types" as never, { body: v } as never)
    },
    onSuccess: () => {
      toast.success("Assessment type created")
      qc.invalidateQueries({ queryKey: queryKeys.refData.assessmentTypes })
      atForm.reset()
      setAtOpen(false)
    },
    onError: () => toast.error("Failed to create assessment type"),
  })

  return (
    <div className="space-y-8">
      <PageHeader
        title="Reference Data"
        description="Manage Bloom's taxonomy levels and assessment types."
      />

      {/* Bloom Domains */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Bloom&apos;s Taxonomy Domains</CardTitle>
          <PermissionGate permission="config.manage">
            <Dialog open={bdOpen} onOpenChange={setBdOpen}>
              <DialogTrigger render={<Button size="sm" />}>
                <Plus /> Add Level
              </DialogTrigger>
              <DialogContent className="sm:max-w-sm">
                <DialogHeader><DialogTitle>Add Bloom Domain</DialogTitle></DialogHeader>
                <form
                  id="bd-form"
                  onSubmit={bdForm.handleSubmit((v) => bdMutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="bd-name">Name</Label>
                    <Input id="bd-name" {...bdForm.register("name")} placeholder="e.g. Remember" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="bd-level">Level (1–6)</Label>
                    <Input id="bd-level" type="number" min={1} max={6} {...bdForm.register("level", { valueAsNumber: true })} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="bd-desc">Description</Label>
                    <Input id="bd-desc" {...bdForm.register("description")} />
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button type="submit" form="bd-form" disabled={bdMutation.isPending}>
                    {bdMutation.isPending && <Loader2 className="animate-spin" />} Create
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </PermissionGate>
        </CardHeader>
        <CardContent>
          {bdLoading ? (
            <div className="space-y-2">
              {[...Array(6)].map((_, i) => <div key={i} className="h-8 bg-muted animate-pulse rounded" />)}
            </div>
          ) : bloomDomains.length === 0 ? (
            <p className="text-sm text-muted-foreground">No Bloom domains configured.</p>
          ) : (
            <div className="space-y-2">
              {bloomDomains
                .sort((a, b) => a.level - b.level)
                .map((bd) => (
                  <div key={bd.id} className="flex items-center gap-3 p-2 rounded-md border text-sm">
                    <Badge variant="secondary" className="shrink-0">L{bd.level}</Badge>
                    <span className="font-medium">{bd.name}</span>
                    {bd.description && (
                      <span className="text-muted-foreground text-xs ml-1">{bd.description}</span>
                    )}
                  </div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Assessment Types */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Assessment Types</CardTitle>
          <PermissionGate permission="config.manage">
            <Dialog open={atOpen} onOpenChange={setAtOpen}>
              <DialogTrigger render={<Button size="sm" />}>
                <Plus /> Add Type
              </DialogTrigger>
              <DialogContent className="sm:max-w-sm">
                <DialogHeader><DialogTitle>Add Assessment Type</DialogTitle></DialogHeader>
                <form
                  id="at-form"
                  onSubmit={atForm.handleSubmit((v) => atMutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="at-name">Name</Label>
                    <Input id="at-name" {...atForm.register("name")} placeholder="e.g. Quiz, Midterm" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="at-desc">Description</Label>
                    <Input id="at-desc" {...atForm.register("description")} />
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button type="submit" form="at-form" disabled={atMutation.isPending}>
                    {atMutation.isPending && <Loader2 className="animate-spin" />} Create
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </PermissionGate>
        </CardHeader>
        <CardContent>
          {atLoading ? (
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => <div key={i} className="h-8 bg-muted animate-pulse rounded" />)}
            </div>
          ) : assessmentTypes.length === 0 ? (
            <p className="text-sm text-muted-foreground">No assessment types configured.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {assessmentTypes.map((at) => (
                <div key={at.id} className="flex items-center gap-2 px-3 py-1.5 rounded-md border text-sm">
                  <span className="font-medium">{at.name}</span>
                  {at.description && <span className="text-muted-foreground text-xs">— {at.description}</span>}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
