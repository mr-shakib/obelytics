"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, useFieldArray } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, Plus, Trash2, ArrowUp, ArrowDown } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { usePermission } from "@/hooks/use-permission"
import type { CourseLearningMaterial } from "../course-types"

const learningMaterialItemSchema = z.object({
  title: z.string().min(1, "Title is required").max(500),
  authors: z.string().max(500).optional(),
  publisher: z.string().max(255).optional(),
  edition_year: z.string().max(100).optional(),
})
const learningMaterialsSchema = z.object({
  textbooks: z.array(learningMaterialItemSchema),
  references: z.array(learningMaterialItemSchema),
})
type LearningMaterialsFormValues = z.infer<typeof learningMaterialsSchema>
type LearningMaterialItemValues = z.infer<typeof learningMaterialItemSchema>
type LearningMaterialPayload = LearningMaterialItemValues & { material_type: "TEXTBOOK" | "REFERENCE" }

interface Props {
  id: string
}

export function CourseMaterialsClient({ id }: Props) {
  const qc = useQueryClient()
  const canEditCourse = usePermission("course.update")

  const { data: learningMaterials = [] } = useQuery({
    queryKey: queryKeys.courseLearningMaterials.byCourse(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/courses/${id}/learning-materials` as never)
      return ((data as unknown) as CourseLearningMaterial[]) ?? []
    },
  })

  const textbooks = learningMaterials.filter((m) => m.material_type === "TEXTBOOK")
  const references = learningMaterials.filter((m) => m.material_type === "REFERENCE")

  const toLearningMaterialFormValues = (m: CourseLearningMaterial): LearningMaterialItemValues => ({
    title: m.title,
    authors: m.authors ?? "",
    publisher: m.publisher ?? "",
    edition_year: m.edition_year ?? "",
  })

  const learningMaterialsForm = useForm<LearningMaterialsFormValues>({
    resolver: zodResolver(learningMaterialsSchema),
    values: {
      textbooks: textbooks.map(toLearningMaterialFormValues),
      references: references.map(toLearningMaterialFormValues),
    },
  })
  const textbooksFieldArray = useFieldArray({ control: learningMaterialsForm.control, name: "textbooks" })
  const referencesFieldArray = useFieldArray({ control: learningMaterialsForm.control, name: "references" })

  const learningMaterialsMutation = useMutation({
    mutationFn: async (materials: LearningMaterialPayload[]) => {
      const { data } = await apiClient.PUT(`/courses/${id}/learning-materials` as never, {
        body: { materials },
      } as never)
      return ((data as unknown) as CourseLearningMaterial[]) ?? []
    },
    onSuccess: (next) => {
      qc.setQueryData(queryKeys.courseLearningMaterials.byCourse(id), next)
      toast.success("Learning materials updated")
    },
    onError: () => toast.error("Failed to update learning materials"),
  })

  const formatLearningMaterial = (m: CourseLearningMaterial) =>
    [m.title, m.authors, m.publisher, m.edition_year].filter(Boolean).join(" — ")

  const renderLearningMaterialFields = (prefix: "textbooks" | "references") => {
    const fieldArray = prefix === "textbooks" ? textbooksFieldArray : referencesFieldArray
    const errors = learningMaterialsForm.formState.errors[prefix]
    return (
      <div className="space-y-3">
        {fieldArray.fields.length === 0 && (
          <p className="text-sm text-muted-foreground">None added yet.</p>
        )}
        {fieldArray.fields.map((field, index) => (
          <div key={field.id} className="rounded-md border border-border p-3 space-y-2">
            <div className="flex items-start gap-2">
              <div className="flex-1 space-y-1">
                <Input placeholder="Title" {...learningMaterialsForm.register(`${prefix}.${index}.title`)} />
                {errors?.[index]?.title && (
                  <p className="text-sm text-destructive">{errors[index]?.title?.message}</p>
                )}
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                disabled={index === 0}
                onClick={() => fieldArray.move(index, index - 1)}
              >
                <ArrowUp />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                disabled={index === fieldArray.fields.length - 1}
                onClick={() => fieldArray.move(index, index + 1)}
              >
                <ArrowDown />
              </Button>
              <Button type="button" variant="ghost" size="icon" onClick={() => fieldArray.remove(index)}>
                <Trash2 />
              </Button>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <Input placeholder="Authors" {...learningMaterialsForm.register(`${prefix}.${index}.authors`)} />
              <Input placeholder="Publisher" {...learningMaterialsForm.register(`${prefix}.${index}.publisher`)} />
              <Input placeholder="Edition / Year" {...learningMaterialsForm.register(`${prefix}.${index}.edition_year`)} />
            </div>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => fieldArray.append({ title: "", authors: "", publisher: "", edition_year: "" })}
        >
          <Plus />
          Add {prefix === "textbooks" ? "textbook" : "reference"}
        </Button>
      </div>
    )
  }

  const onSubmitLearningMaterials = learningMaterialsForm.handleSubmit((values) => {
    const toMaterial = (type: "TEXTBOOK" | "REFERENCE") => (item: LearningMaterialItemValues) => ({
      material_type: type,
      title: item.title.trim(),
      authors: item.authors?.trim() || undefined,
      publisher: item.publisher?.trim() || undefined,
      edition_year: item.edition_year?.trim() || undefined,
    })
    learningMaterialsMutation.mutate([
      ...values.textbooks.map(toMaterial("TEXTBOOK")),
      ...values.references.map(toMaterial("REFERENCE")),
    ])
  })

  return (
    <Card>
      <CardHeader><CardTitle>Learning Materials</CardTitle></CardHeader>
      <CardContent>
        {canEditCourse ? (
          <form onSubmit={onSubmitLearningMaterials} className="space-y-6">
            <div className="space-y-3">
              <h4 className="text-sm font-medium">Textbooks</h4>
              {renderLearningMaterialFields("textbooks")}
            </div>
            <div className="space-y-3">
              <h4 className="text-sm font-medium">References</h4>
              {renderLearningMaterialFields("references")}
            </div>
            <Button
              type="submit"
              size="sm"
              disabled={!learningMaterialsForm.formState.isDirty || learningMaterialsMutation.isPending}
            >
              {learningMaterialsMutation.isPending && <Loader2 className="animate-spin" />}
              Save Learning Materials
            </Button>
          </form>
        ) : textbooks.length === 0 && references.length === 0 ? (
          <p className="text-sm text-muted-foreground">No learning materials added yet.</p>
        ) : (
          <div className="space-y-4">
            {textbooks.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-1">Textbooks</h4>
                <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                  {textbooks.map((m) => (
                    <li key={m.id}>{formatLearningMaterial(m)}</li>
                  ))}
                </ul>
              </div>
            )}
            {references.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-1">References</h4>
                <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                  {references.map((m) => (
                    <li key={m.id}>{formatLearningMaterial(m)}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
