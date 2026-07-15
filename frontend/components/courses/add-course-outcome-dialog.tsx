"use client"

import { useEffect, useState } from "react"
import { Controller, useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Plus } from "lucide-react"
import { toast } from "sonner"
import { z } from "zod"
import { BloomLevelCheckboxGroup } from "@/components/shared/bloom-level-checkbox-group"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type BloomDomain = { id: string; name: string }
type BloomLevel = {
  id: string
  code: string
  name: string
  bloom_domain_id: string
  order_index: number
}

const schema = z.object({
  code: z.string().min(1, "Code is required").max(20),
  statement: z.string().min(10, "At least 10 characters"),
  bloom_level_ids: z.array(z.string()),
})

type FormValues = z.infer<typeof schema>

interface Props {
  curriculumId: string
  courseId: string
  nextOutcomeNumber: number
}

export function AddCourseOutcomeDialog({ curriculumId, courseId, nextOutcomeNumber }: Props) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const suggestedCode = `CO${nextOutcomeNumber}`
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { code: suggestedCode, statement: "", bloom_level_ids: [] },
  })

  useEffect(() => {
    if (open) {
      form.reset({ code: suggestedCode, statement: "", bloom_level_ids: [] })
    }
  }, [form, open, suggestedCode])

  const { data: bloomLevels = [] } = useQuery({
    queryKey: queryKeys.refData.bloomLevels,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-levels" as never)
      return ((data as unknown) as BloomLevel[]) ?? []
    },
  })

  const { data: bloomDomains = [] } = useQuery({
    queryKey: queryKeys.refData.bloomDomains,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-domains" as never)
      return (
        ((data as unknown) as { items?: BloomDomain[] })?.items ??
        ((data as unknown) as BloomDomain[]) ??
        []
      )
    },
  })

  const addMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.POST("/course-outcomes" as never, {
        body: { curriculum_id: curriculumId, course_id: courseId, ...values },
      } as never)
    },
    onSuccess: () => {
      toast.success("Course Outcome added")
      queryClient.invalidateQueries({
        queryKey: queryKeys.courseOutcomes.list(curriculumId, courseId),
      })
      setOpen(false)
    },
    onError: () => toast.error("Failed to add CO"),
  })

  return (
    <>
      <PermissionGate permission="co.create">
        <Button onClick={() => setOpen(true)}>
          <Plus />
          Add CO
        </Button>
      </PermissionGate>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Add Course Outcome</DialogTitle>
          </DialogHeader>
          <form
            id="course-mapping-co-form"
            onSubmit={form.handleSubmit((values) => addMutation.mutate(values))}
            className="space-y-4 py-2"
          >
            <div className="space-y-2">
              <Label htmlFor="mapping-co-code">Code</Label>
              <Input id="mapping-co-code" {...form.register("code")} placeholder={suggestedCode} />
              {form.formState.errors.code && (
                <p className="text-sm text-destructive">{form.formState.errors.code.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="mapping-co-statement">Statement</Label>
              <Textarea
                id="mapping-co-statement"
                {...form.register("statement")}
                placeholder="Describe what students will be able to do..."
                rows={4}
              />
              {form.formState.errors.statement && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.statement.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label>
                Bloom Level{" "}
                <span className="font-normal text-muted-foreground">(optional, multiple allowed)</span>
              </Label>
              <Controller
                name="bloom_level_ids"
                control={form.control}
                render={({ field }) => (
                  <BloomLevelCheckboxGroup
                    bloomDomains={bloomDomains}
                    bloomLevels={bloomLevels}
                    value={field.value}
                    onChange={field.onChange}
                  />
                )}
              />
            </div>
          </form>
          <DialogFooter showCloseButton>
            <Button
              type="submit"
              form="course-mapping-co-form"
              disabled={addMutation.isPending}
            >
              {addMutation.isPending && <Loader2 className="animate-spin" />}
              Add CO
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
