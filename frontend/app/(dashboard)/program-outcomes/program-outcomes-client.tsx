"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import type { ColumnDef } from "@tanstack/react-table"
import { DataTable } from "@/components/shared/data-table"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
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
import { truncate } from "@/lib/utils"

type ProgramOutcome = {
  id: string
  code: string
  statement: string
  bloom_level_name?: string
  program_name?: string
  status: string
}

type Program = { id: string; name: string }
type BloomDomain = { id: string; name: string }

const schema = z.object({
  program_id: z.string().min(1, "Program is required"),
  code: z.string().min(1, "Code is required"),
  statement: z.string().min(1, "Statement is required").max(500, "Max 500 characters"),
  bloom_level_id: z.string().min(1, "Bloom level is required"),
})
type FormValues = z.infer<typeof schema>

const columns: ColumnDef<ProgramOutcome>[] = [
  { accessorKey: "code", header: "Code" },
  {
    accessorKey: "statement",
    header: "Statement",
    cell: ({ row }) => (
      <span title={row.original.statement}>{truncate(row.original.statement, 80)}</span>
    ),
  },
  {
    accessorKey: "bloom_level_name",
    header: "Bloom Level",
    cell: ({ row }) =>
      row.original.bloom_level_name ?? (
        <span className="text-muted-foreground">—</span>
      ),
  },
  {
    accessorKey: "program_name",
    header: "Program",
    cell: ({ row }) =>
      row.original.program_name ?? (
        <span className="text-muted-foreground">—</span>
      ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
]

export function ProgramOutcomesClient() {
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.programOutcomes.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/program-outcomes" as never)
      return ((data as unknown) as { items?: ProgramOutcome[] })?.items ?? ((data as unknown) as ProgramOutcome[]) ?? []
    },
  })

  const { data: programs } = useQuery({
    queryKey: queryKeys.programs.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/programs" as never)
      return ((data as unknown) as { items?: Program[] })?.items ?? ((data as unknown) as Program[]) ?? []
    },
  })

  const { data: bloomDomains } = useQuery({
    queryKey: queryKeys.refData.bloomDomains,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-domains" as never)
      return ((data as unknown) as { items?: BloomDomain[] })?.items ?? ((data as unknown) as BloomDomain[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.POST("/program-outcomes" as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Program Outcome created")
      qc.invalidateQueries({ queryKey: queryKeys.programOutcomes.all })
      reset()
      setOpen(false)
    },
    onError: () => toast.error("Failed to create Program Outcome"),
  })

  return (
    <div>
      <PageHeader
        title="Program Outcomes"
        description="Manage program-level learning outcomes."
        actions={
          <PermissionGate permission="po.create">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger
                render={
                  <Button>
                    <Plus />
                    New PO
                  </Button>
                }
              />
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>Create Program Outcome</DialogTitle>
                </DialogHeader>
                <form
                  id="create-po-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="po-program">Program</Label>
                    <Controller
                      name="program_id"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select program" />
                          </SelectTrigger>
                          <SelectContent>
                            {(programs ?? []).map((p) => (
                              <SelectItem key={p.id} value={p.id}>
                                {p.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.program_id && (
                      <p className="text-sm text-destructive">{errors.program_id.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="po-code">Code</Label>
                    <Input id="po-code" {...register("code")} placeholder="PO1" />
                    {errors.code && (
                      <p className="text-sm text-destructive">{errors.code.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="po-statement">Statement</Label>
                    <Textarea
                      id="po-statement"
                      {...register("statement")}
                      placeholder="Describe the program outcome..."
                      rows={4}
                      maxLength={500}
                    />
                    {errors.statement && (
                      <p className="text-sm text-destructive">{errors.statement.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="po-bloom">Bloom Level</Label>
                    <Controller
                      name="bloom_level_id"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select bloom level" />
                          </SelectTrigger>
                          <SelectContent>
                            {(bloomDomains ?? []).map((b) => (
                              <SelectItem key={b.id} value={b.id}>
                                {b.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.bloom_level_id && (
                      <p className="text-sm text-destructive">{errors.bloom_level_id.message}</p>
                    )}
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button
                    type="submit"
                    form="create-po-form"
                    disabled={isSubmitting || mutation.isPending}
                  >
                    {(isSubmitting || mutation.isPending) && (
                      <Loader2 className="animate-spin" />
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
        data={data ?? []}
        loading={isLoading}
        onRowClick={(row) => router.push(`/program-outcomes/${row.id}`)}
        emptyMessage="No program outcomes found."
      />
    </div>
  )
}
