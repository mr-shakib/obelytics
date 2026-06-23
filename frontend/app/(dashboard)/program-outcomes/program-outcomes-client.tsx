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
  program_id: string
  bloom_domain_id?: string | null
  po_type?: string | null
  status: string
}

type Program = { id: string; title?: string; name?: string; acronym?: string }
type BloomDomain = { id: string; name: string }
type POType = { id: string; name: string; is_active: boolean }

const NONE_PO_TYPE = "none"

const schema = z.object({
  program_id: z.string().optional(),
  code: z.string().min(1, "Code is required"),
  statement: z.string().min(1, "Statement is required").max(500, "Max 500 characters"),
  bloom_domain_id: z.string().min(1, "Bloom domain is required"),
  po_type: z.string().optional(),
})
type FormValues = z.infer<typeof schema>

function programLabel(p: Program): string {
  const title = p.title ?? p.name ?? ""
  return p.acronym ? `${p.acronym} — ${title}` : title
}

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

  const { data: bloomDomains = [] } = useQuery({
    queryKey: queryKeys.refData.bloomDomains,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-domains" as never)
      return ((data as unknown) as { items?: BloomDomain[] })?.items ?? ((data as unknown) as BloomDomain[]) ?? []
    },
  })

  const { data: poTypes = [] } = useQuery({
    queryKey: queryKeys.refData.poTypes,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/po-types" as never)
      return ((data as unknown) as { items?: POType[] })?.items ?? ((data as unknown) as POType[]) ?? []
    },
  })

  const programById = Object.fromEntries((programs ?? []).map((p) => [p.id, p]))
  const bloomDomainById = Object.fromEntries(bloomDomains.map((d) => [d.id, d]))
  const activePoTypes = poTypes.filter((t) => t.is_active)

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
      accessorKey: "bloom_domain_id",
      header: "Bloom Domain",
      cell: ({ row }) =>
        bloomDomainById[row.original.bloom_domain_id ?? ""]?.name ?? (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      accessorKey: "program_id",
      header: "Program",
      cell: ({ row }) => {
        const program = programById[row.original.program_id]
        return program ? programLabel(program) : <span className="text-muted-foreground">—</span>
      },
    },
    {
      accessorKey: "po_type",
      header: "PO Type",
      cell: ({ row }) =>
        row.original.po_type ?? <span className="text-muted-foreground">—</span>,
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
  ]

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const order_index = (data ?? []).length
      await apiClient.POST("/program-outcomes" as never, {
        body: {
          program_id: values.program_id || undefined,
          code: values.code,
          statement: values.statement,
          bloom_domain_id: values.bloom_domain_id,
          po_type: values.po_type === NONE_PO_TYPE ? undefined : values.po_type,
          order_index,
        },
      } as never)
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
                    <Label htmlFor="po-program">Program (optional — leave empty for global POs)</Label>
                    <Controller
                      name="program_id"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={(v) => field.onChange(v === NONE_PO_TYPE ? "" : v)}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="All programs (global)" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value={NONE_PO_TYPE}>All programs (global)</SelectItem>
                            {(programs ?? []).map((p) => (
                              <SelectItem key={p.id} value={p.id}>
                                {programLabel(p)}
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
                    <Label htmlFor="po-bloom">Bloom Domain</Label>
                    <Controller
                      name="bloom_domain_id"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select bloom domain" />
                          </SelectTrigger>
                          <SelectContent>
                            {bloomDomains.map((domain) => (
                              <SelectItem key={domain.id} value={domain.id}>
                                {domain.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.bloom_domain_id && (
                      <p className="text-sm text-destructive">{errors.bloom_domain_id.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="po-type">PO Type</Label>
                    <Controller
                      name="po_type"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? NONE_PO_TYPE} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select PO type" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value={NONE_PO_TYPE}>— None —</SelectItem>
                            {activePoTypes.map((t) => (
                              <SelectItem key={t.id} value={t.name}>
                                {t.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.po_type && (
                      <p className="text-sm text-destructive">{errors.po_type.message}</p>
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
