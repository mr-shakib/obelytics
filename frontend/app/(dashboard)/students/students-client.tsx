"use client"

import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { useRouter } from "next/navigation"
import { Plus, Loader2, Upload, Search } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"
import { DataTable } from "@/components/shared/data-table"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Student = {
  id: string
  student_id_number: string
  full_name: string
  email: string | null
  status: string
}

const addSchema = z.object({
  student_id_number: z.string().min(1, "Student ID is required"),
  full_name: z.string().min(1, "Name is required"),
  email: z.union([z.string().email("Enter a valid email"), z.literal("")]).optional(),
})
type AddFormValues = z.infer<typeof addSchema>

const columns: ColumnDef<Student>[] = [
  { accessorKey: "student_id_number", header: "Student ID" },
  { accessorKey: "full_name", header: "Name" },
  {
    accessorKey: "email",
    header: "Email",
    cell: ({ row }) => row.original.email ?? <span className="text-muted-foreground">—</span>,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
]

export function StudentsClient() {
  const router = useRouter()
  const qc = useQueryClient()
  const [addOpen, setAddOpen] = useState(false)
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(t)
  }, [search])

  const { data: students = [], isLoading } = useQuery({
    queryKey: queryKeys.students.list({ search: debouncedSearch }),
    queryFn: async () => {
      const { data } = await apiClient.GET("/students" as never, {
        params: { query: debouncedSearch ? { search: debouncedSearch } : {} },
      } as never)
      return ((data as unknown) as Student[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AddFormValues>({ resolver: zodResolver(addSchema) })

  const addMutation = useMutation({
    mutationFn: async (values: AddFormValues) => {
      await apiClient.POST("/students" as never, {
        body: { ...values, email: values.email || null },
      } as never)
    },
    onSuccess: () => {
      toast.success("Student added")
      qc.invalidateQueries({ queryKey: queryKeys.students.all })
      reset()
      setAddOpen(false)
    },
    onError: () => toast.error("Failed to add student"),
  })

  return (
    <div className="space-y-4">
      <PageHeader
        title="Students"
        description="System-wide student registry. Section teachers enroll students from this registry into their course sections."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => router.push("/students/import")}>
              <Upload />
              Bulk Import
            </Button>

            <Dialog open={addOpen} onOpenChange={setAddOpen}>
              <DialogTrigger
                render={
                  <Button>
                    <Plus />
                    Add Student
                  </Button>
                }
              />
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Add Student</DialogTitle>
                </DialogHeader>
                <form
                  id="add-student-form"
                  onSubmit={handleSubmit((v) => addMutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="student-id">Student ID</Label>
                    <Input id="student-id" {...register("student_id_number")} placeholder="221-15-1234" />
                    {errors.student_id_number && (
                      <p className="text-sm text-destructive">{errors.student_id_number.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="student-name">Full Name</Label>
                    <Input id="student-name" {...register("full_name")} placeholder="Jane Doe" />
                    {errors.full_name && (
                      <p className="text-sm text-destructive">{errors.full_name.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="student-email">Email (optional)</Label>
                    <Input id="student-email" type="email" {...register("email")} placeholder="jane@example.com" />
                    {errors.email && (
                      <p className="text-sm text-destructive">{errors.email.message}</p>
                    )}
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button type="submit" form="add-student-form" disabled={isSubmitting || addMutation.isPending}>
                    {(isSubmitting || addMutation.isPending) && <Loader2 className="animate-spin" />}
                    Add
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        }
      />

      <div className="relative max-w-sm">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          className="pl-8"
          placeholder="Search by ID or name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <DataTable columns={columns} data={students} loading={isLoading} emptyMessage="No students found." />
    </div>
  )
}
