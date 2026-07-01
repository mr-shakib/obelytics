"use client"

import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2, ChevronRight, Layers } from "lucide-react"
import { useRouter } from "next/navigation"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent } from "@/components/ui/card"
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
import { usePermissions } from "@/hooks/use-permission"
import { useAuthStore } from "@/lib/stores/auth-store"

type POVersion = {
  id: string
  name: string
  description: string | null
  is_active: boolean
  po_count: number
  created_at: string
}

const schema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  description: z.string().optional(),
})
type FormValues = z.infer<typeof schema>

export function ProgramOutcomesClient() {
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const qc = useQueryClient()
  const permissions = usePermissions()
  const isInitialized = useAuthStore((state) => state.isInitialized)
  const canManageProgramOutcomes = permissions.some((permission) =>
    ["po.create", "po.update", "po.archive"].includes(permission)
  )

  useEffect(() => {
    if (isInitialized && !canManageProgramOutcomes) {
      router.replace("/overview")
    }
  }, [canManageProgramOutcomes, isInitialized, router])

  const { data: versions = [], isLoading } = useQuery({
    queryKey: queryKeys.poVersions.list(),
    enabled: isInitialized && canManageProgramOutcomes,
    queryFn: async () => {
      const { data } = await apiClient.GET("/po-versions" as never)
      return ((data as unknown) as POVersion[]) ?? []
    },
  })

  if (!isInitialized || !canManageProgramOutcomes) return null

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.POST("/po-versions" as never, {
        body: values,
      } as never)
    },
    onSuccess: () => {
      toast.success("PO Version created")
      qc.invalidateQueries({ queryKey: queryKeys.poVersions.all })
      reset()
      setOpen(false)
    },
    onError: () => toast.error("Failed to create PO Version"),
  })

  return (
    <div>
      <PageHeader
        title="Program Outcomes"
        description="Manage PO versions and their program outcomes."
        actions={
          <PermissionGate permission="po.create">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger
                render={
                  <Button>
                    <Plus />
                    New Version
                  </Button>
                }
              />
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Create PO Version</DialogTitle>
                </DialogHeader>
                <form
                  id="create-version-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="version-name">Name</Label>
                    <Input
                      id="version-name"
                      {...register("name")}
                      placeholder="e.g. Version 2.1"
                    />
                    {errors.name && (
                      <p className="text-sm text-destructive">{errors.name.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="version-description">Description</Label>
                    <Textarea
                      id="version-description"
                      {...register("description")}
                      placeholder="Optional description..."
                      rows={3}
                    />
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button
                    type="submit"
                    form="create-version-form"
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

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      ) : versions.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Layers className="mx-auto h-10 w-10 text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No PO versions yet. Create one to get started.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {versions.map((v) => (
            <Card
              key={v.id}
              className="cursor-pointer transition-colors hover:bg-muted/50"
              onClick={() => router.push(`/program-outcomes/${v.id}`)}
            >
              <CardContent className="py-5">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <h3 className="font-semibold text-base">{v.name}</h3>
                    {v.description && (
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {v.description}
                      </p>
                    )}
                  </div>
                  <ChevronRight className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                </div>
                <div className="mt-4 flex items-center gap-3 text-sm text-muted-foreground">
                  <span className="inline-flex items-center gap-1 rounded-md bg-secondary px-2 py-0.5 text-xs font-medium">
                    {v.po_count} PO{v.po_count !== 1 ? "s" : ""}
                  </span>
                  <span>
                    Created{" "}
                    {new Date(v.created_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
