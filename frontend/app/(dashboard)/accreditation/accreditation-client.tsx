"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2, Award } from "lucide-react"
import Link from "next/link"
import { format } from "date-fns"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
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

type AccreditationCycle = {
  id: string
  name: string
  body: string
  start_date: string
  end_date?: string
  status: "ACTIVE" | "CLOSED" | "DRAFT"
  program_name?: string
}

type ProgramOption = { id: string; title: string; acronym: string }

const cycleSchema = z.object({
  name: z.string().min(1, "Name required"),
  body: z.string().min(1, "Accreditation body required"),
  start_date: z.string().min(1, "Start date required"),
  end_date: z.string().optional(),
  program_id: z.string().min(1, "Program required"),
})
type CycleForm = z.infer<typeof cycleSchema>

const STATUS_VARIANT: Record<AccreditationCycle["status"], "default" | "secondary" | "destructive"> = {
  ACTIVE: "default",
  DRAFT: "secondary",
  CLOSED: "secondary",
}

export function AccreditationClient() {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)

  const { data: cycles, isLoading } = useQuery({
    queryKey: queryKeys.accreditation.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/accreditation/cycles" as never)
      return ((data as unknown) as { items?: AccreditationCycle[] })?.items ?? ((data as unknown) as AccreditationCycle[]) ?? []
    },
  })

  const { data: programs } = useQuery({
    queryKey: queryKeys.programs.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/programs" as never)
      return ((data as unknown) as ProgramOption[]) ?? []
    },
  })

  const form = useForm<CycleForm>({ resolver: zodResolver(cycleSchema) })

  const createMutation = useMutation({
    mutationFn: async (v: CycleForm) => {
      await apiClient.POST("/accreditation/cycles" as never, { body: v } as never)
    },
    onSuccess: () => {
      toast.success("Accreditation cycle created")
      qc.invalidateQueries({ queryKey: queryKeys.accreditation.all })
      form.reset()
      setOpen(false)
    },
    onError: () => toast.error("Failed to create cycle"),
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Accreditation"
        description="Manage accreditation cycles and self-study reports."
        actions={
          <PermissionGate permission="accreditation.manage">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger render={<Button size="sm" />}>
                <Plus /> New Cycle
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader><DialogTitle>Create Accreditation Cycle</DialogTitle></DialogHeader>
                <form
                  id="cycle-form"
                  onSubmit={form.handleSubmit((v) => createMutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="cy-name">Cycle Name</Label>
                    <Input id="cy-name" {...form.register("name")} placeholder="e.g. ABET 2024–2025" />
                    {form.formState.errors.name && (
                      <p className="text-xs text-destructive">{form.formState.errors.name.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="cy-body">Accreditation Body</Label>
                    <Input id="cy-body" {...form.register("body")} placeholder="e.g. ABET, AACSB" />
                  </div>
                  <div className="space-y-2">
                    <Label>Program</Label>
                    <Controller
                      name="program_id"
                      control={form.control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select program">
                              {(value: string) => value
                                ? ((programs ?? []).find((p) => p.id === value)?.title ?? value)
                                : null}
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {(programs ?? []).map((p) => (
                              <SelectItem key={p.id} value={p.id}>{p.title} ({p.acronym})</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {form.formState.errors.program_id && (
                      <p className="text-xs text-destructive">{form.formState.errors.program_id.message}</p>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label htmlFor="cy-start">Start Date</Label>
                      <Input id="cy-start" type="date" {...form.register("start_date")} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="cy-end">End Date</Label>
                      <Input id="cy-end" type="date" {...form.register("end_date")} />
                    </div>
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button type="submit" form="cycle-form" disabled={createMutation.isPending}>
                    {createMutation.isPending && <Loader2 className="animate-spin" />} Create
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </PermissionGate>
        }
      />

      {isLoading && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <div key={i} className="h-20 bg-muted animate-pulse rounded-md" />)}
        </div>
      )}

      {!isLoading && (cycles ?? []).length === 0 && (
        <div className="flex flex-col items-center gap-3 py-12 text-muted-foreground">
          <Award className="h-8 w-8" />
          <p className="text-sm">No accreditation cycles yet.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(cycles ?? []).map((cycle) => (
          <Card key={cycle.id} className="hover:shadow-sm transition-shadow">
            <CardContent className="p-4 space-y-2">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-sm">{cycle.name}</p>
                  <p className="text-xs text-muted-foreground">{cycle.body}</p>
                  {cycle.program_name && (
                    <p className="text-xs text-muted-foreground">{cycle.program_name}</p>
                  )}
                </div>
                <Badge variant={STATUS_VARIANT[cycle.status]}>{cycle.status}</Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                {format(new Date(cycle.start_date), "MMM yyyy")}
                {cycle.end_date && ` — ${format(new Date(cycle.end_date), "MMM yyyy")}`}
              </p>
              <Button variant="outline" size="sm" className="w-full mt-1" render={<Link href={`/accreditation/${cycle.id}`} />}>
                Open Cycle
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
