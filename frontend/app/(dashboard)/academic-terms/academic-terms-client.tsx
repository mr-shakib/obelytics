"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2 } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"

import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/shared/data-table"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { formatDate } from "@/lib/utils"

type AcademicTerm = {
  id: string
  name: string
  term_type: string
  year: number
  start_date: string
  end_date: string
  status: string
}

const TERM_TYPES = ["SEMESTER", "TRIMESTER", "ANNUAL"] as const

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  term_type: z.enum(TERM_TYPES),
  year: z.number().int().min(2000).max(2100),
  start_date: z.string().min(1, "Start date is required"),
  end_date: z.string().min(1, "End date is required"),
})
type FormValues = z.infer<typeof schema>

const columns: ColumnDef<AcademicTerm>[] = [
  { accessorKey: "name", header: "Name" },
  { accessorKey: "term_type", header: "Type" },
  { accessorKey: "year", header: "Year" },
  {
    accessorKey: "start_date",
    header: "Start Date",
    cell: ({ row }) => formatDate(row.original.start_date),
  },
  {
    accessorKey: "end_date",
    header: "End Date",
    cell: ({ row }) => formatDate(row.original.end_date),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
]

export function AcademicTermsClient() {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()

  const { data: terms = [], isLoading } = useQuery({
    queryKey: queryKeys.academicTerms.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/academic-terms" as never)
      return ((data as unknown) as AcademicTerm[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.POST("/academic-terms" as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Academic term created")
      qc.invalidateQueries({ queryKey: queryKeys.academicTerms.all })
      setOpen(false)
      reset()
    },
    onError: () => toast.error("Failed to create academic term"),
  })

  return (
    <div>
      <PageHeader
        title="Academic Terms"
        description="Manage academic terms and semesters."
        actions={
          <PermissionGate permission="curriculum.read">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger render={<Button />}>
                <Plus className="h-4 w-4" />
                New Term
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Create Academic Term</DialogTitle>
                </DialogHeader>
                <form
                  id="create-term-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input id="name" {...register("name")} placeholder="e.g. Fall 2024" />
                    {errors.name && (
                      <p className="text-sm text-destructive">{errors.name.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Term Type</Label>
                    <Select onValueChange={(v) => v != null && setValue("term_type", v as FormValues["term_type"])}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        {TERM_TYPES.map((t) => (
                          <SelectItem key={t} value={t}>
                            {t}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.term_type && (
                      <p className="text-sm text-destructive">{errors.term_type.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="year">Year</Label>
                    <Input id="year" type="number" min={2000} max={2100} {...register("year", { valueAsNumber: true })} />
                    {errors.year && (
                      <p className="text-sm text-destructive">{errors.year.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="start_date">Start Date</Label>
                    <Input id="start_date" type="date" {...register("start_date")} />
                    {errors.start_date && (
                      <p className="text-sm text-destructive">{errors.start_date.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="end_date">End Date</Label>
                    <Input id="end_date" type="date" {...register("end_date")} />
                    {errors.end_date && (
                      <p className="text-sm text-destructive">{errors.end_date.message}</p>
                    )}
                  </div>
                </form>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setOpen(false)}
                    disabled={isSubmitting || mutation.isPending}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    form="create-term-form"
                    disabled={isSubmitting || mutation.isPending}
                  >
                    {(isSubmitting || mutation.isPending) && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    Create
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </PermissionGate>
        }
      />
      <DataTable
        columns={columns}
        data={terms}
        loading={isLoading}
        emptyMessage="No academic terms found."
      />
    </div>
  )
}
