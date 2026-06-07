"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, useFieldArray } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, ArrowLeft, Plus, Trash2 } from "lucide-react"
import Link from "next/link"
import { useState } from "react"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type CourseOutcome = {
  id: string
  code: string
  statement: string
  course_name?: string
  course_id?: string
}

type ProgramOutcome = { id: string; code: string; statement: string }

type CoMapping = {
  id: string
  po_id: string
  po_code: string
  strength: 1 | 2 | 3
}

const STRENGTH_LABELS: Record<1 | 2 | 3, string> = { 1: "Low", 2: "Medium", 3: "High" }

const mappingSchema = z.object({
  mappings: z.array(z.object({
    po_id: z.string().min(1, "PO required"),
    strength: z.number().int().min(1).max(3),
  })),
})
type MappingForm = z.infer<typeof mappingSchema>

interface Props {
  coId: string
}

export function CoMappingsClient({ coId }: Props) {
  const qc = useQueryClient()
  const [dirty, setDirty] = useState(false)

  const { data: co, isLoading: coLoading } = useQuery({
    queryKey: queryKeys.courseOutcomes.detail(coId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/course-outcomes/${coId}` as never)
      return (data as unknown) as CourseOutcome
    },
  })

  const { data: existingMappings, isLoading: mappingsLoading } = useQuery({
    queryKey: queryKeys.courseOutcomes.mappings(coId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/course-outcomes/${coId}/mappings` as never)
      return ((data as unknown) as { items?: CoMapping[] })?.items ?? ((data as unknown) as CoMapping[]) ?? []
    },
  })

  const { data: programOutcomes } = useQuery({
    queryKey: queryKeys.programOutcomes.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/program-outcomes" as never)
      return ((data as unknown) as { items?: ProgramOutcome[] })?.items ?? ((data as unknown) as ProgramOutcome[]) ?? []
    },
  })

  const form = useForm<MappingForm>({
    resolver: zodResolver(mappingSchema),
    defaultValues: { mappings: [] },
    values: {
      mappings: (existingMappings ?? []).map((m) => ({
        po_id: m.po_id,
        strength: m.strength,
      })),
    },
  })

  const { fields, append, remove } = useFieldArray({ control: form.control, name: "mappings" })

  const saveMutation = useMutation({
    mutationFn: async (v: MappingForm) => {
      await apiClient.PUT(`/course-outcomes/${coId}/mappings` as never, {
        body: { mappings: v.mappings },
      } as never)
    },
    onSuccess: () => {
      toast.success("CO mappings saved")
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.mappings(coId) })
      setDirty(false)
    },
    onError: () => toast.error("Failed to save mappings"),
  })

  const isLoading = coLoading || mappingsLoading

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!co) return <p className="text-muted-foreground">Course outcome not found.</p>

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeader
        title={`${co.code} Mappings`}
        description={co.statement}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" render={<Link href={`/course-outcomes/${coId}`} />}>
              <ArrowLeft /> Back
            </Button>
          </div>
        }
      />

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">
            {co.course_name && (
              <span className="text-muted-foreground font-normal">{co.course_name} · </span>
            )}
            Program Outcome Mappings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={form.handleSubmit((v) => saveMutation.mutate(v))}
            className="space-y-4"
          >
            {fields.map((field, i) => {
              const po = (programOutcomes ?? []).find((p) => p.id === form.watch(`mappings.${i}.po_id`))
              return (
                <div key={field.id} className="flex items-center gap-3">
                  <div className="flex-1">
                    <Select
                      value={form.watch(`mappings.${i}.po_id`)}
                      onValueChange={(v) => {
                        if (v == null) return
                        form.setValue(`mappings.${i}.po_id`, v as string)
                        setDirty(true)
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select PO" />
                      </SelectTrigger>
                      <SelectContent>
                        {(programOutcomes ?? []).map((p) => (
                          <SelectItem key={p.id} value={p.id}>
                            {p.code} — {p.statement.slice(0, 60)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Select
                    value={String(form.watch(`mappings.${i}.strength`))}
                    onValueChange={(v) => {
                      if (v == null) return
                      form.setValue(`mappings.${i}.strength`, Number(v as string) as 1 | 2 | 3)
                      setDirty(true)
                    }}
                  >
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {([1, 2, 3] as const).map((s) => (
                        <SelectItem key={s} value={String(s)}>
                          {STRENGTH_LABELS[s]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => { remove(i); setDirty(true) }}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              )
            })}

            <PermissionGate permission="co.po.map">
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => { append({ po_id: "", strength: 1 }); setDirty(true) }}
                >
                  <Plus /> Add Mapping
                </Button>
                {dirty && (
                  <Button type="submit" size="sm" disabled={saveMutation.isPending}>
                    {saveMutation.isPending && <Loader2 className="animate-spin" />}
                    Save
                  </Button>
                )}
              </div>
            </PermissionGate>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
