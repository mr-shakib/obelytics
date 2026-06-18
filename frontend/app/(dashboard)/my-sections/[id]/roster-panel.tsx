"use client"

import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, Search, Trash2, UserPlus, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog"
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui/table"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type RosterEntry = {
  id: string
  student_id: string
  student_id_number: string
  full_name: string
  email: string | null
  status: string
  enrolled_at: string
}

type StudentSearchResult = {
  id: string
  student_id_number: string
  full_name: string
  email: string | null
}

type BulkEnrollResult = { enrolled: number; already_enrolled: number; not_found: number }

interface Props {
  sectionOfferingId: string
  locked?: boolean
}

function EnrollDialog({ sectionOfferingId, roster }: Props & { roster: RosterEntry[] }) {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [pending, setPending] = useState<Map<string, StudentSearchResult>>(new Map())

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(t)
  }, [search])

  const enrolledIds = new Set(roster.map((r) => r.student_id))

  const { data: results = [], isFetching } = useQuery({
    queryKey: queryKeys.students.list({ search: debouncedSearch }),
    queryFn: async () => {
      const { data } = await apiClient.GET("/students" as never, {
        params: { query: debouncedSearch ? { search: debouncedSearch } : {} },
      } as never)
      return ((data as unknown) as StudentSearchResult[]) ?? []
    },
    enabled: debouncedSearch.length > 0,
  })

  const bulkEnrollMutation = useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.POST("/enrollments/bulk" as never, {
        body: { section_offering_id: sectionOfferingId, student_ids: Array.from(pending.keys()) },
      } as never)
      return (data as unknown) as BulkEnrollResult
    },
    onSuccess: (result) => {
      toast.success(
        `Enrolled ${result.enrolled} student${result.enrolled === 1 ? "" : "s"}` +
          (result.already_enrolled ? ` (${result.already_enrolled} already enrolled)` : "")
      )
      qc.invalidateQueries({ queryKey: queryKeys.enrollments.roster(sectionOfferingId) })
      setPending(new Map())
      setOpen(false)
    },
    onError: () => toast.error("Failed to enroll students"),
  })

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o)
        if (!o) {
          setPending(new Map())
          setSearch("")
        }
      }}
    >
      <DialogTrigger
        render={
          <Button size="sm">
            <UserPlus />
            Enroll Students
          </Button>
        }
      />
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Enroll Students</DialogTitle>
          <DialogDescription>
            Search the student registry and add students to this section.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-8"
              placeholder="Search by ID or name…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>

          {pending.size > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {Array.from(pending.values()).map((s) => (
                <Badge key={s.id} variant="secondary" className="gap-1">
                  {s.student_id_number} — {s.full_name}
                  <button
                    type="button"
                    onClick={() =>
                      setPending((prev) => {
                        const next = new Map(prev)
                        next.delete(s.id)
                        return next
                      })
                    }
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          )}

          <div className="max-h-64 overflow-y-auto rounded-md border">
            {isFetching ? (
              <div className="flex justify-center py-6">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            ) : debouncedSearch.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                Start typing to search students.
              </p>
            ) : results.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">No students found.</p>
            ) : (
              <ul className="divide-y">
                {results.map((s) => {
                  const alreadyEnrolled = enrolledIds.has(s.id)
                  const isPending = pending.has(s.id)
                  return (
                    <li key={s.id} className="flex items-center justify-between px-3 py-2 text-sm">
                      <div>
                        <span className="font-medium">{s.student_id_number}</span> — {s.full_name}
                      </div>
                      <Button
                        size="sm"
                        variant={isPending ? "secondary" : "outline"}
                        disabled={alreadyEnrolled}
                        onClick={() =>
                          setPending((prev) => {
                            const next = new Map(prev)
                            if (next.has(s.id)) next.delete(s.id)
                            else next.set(s.id, s)
                            return next
                          })
                        }
                      >
                        {alreadyEnrolled ? "Enrolled" : isPending ? "Added" : "Add"}
                      </Button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </div>
        <DialogFooter showCloseButton>
          <Button
            onClick={() => bulkEnrollMutation.mutate()}
            disabled={pending.size === 0 || bulkEnrollMutation.isPending}
          >
            {bulkEnrollMutation.isPending && <Loader2 className="animate-spin" />}
            Enroll {pending.size > 0 ? pending.size : ""}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function RosterPanel({ sectionOfferingId, locked = false }: Props) {
  const qc = useQueryClient()

  const { data: roster = [], isLoading } = useQuery({
    queryKey: queryKeys.enrollments.roster(sectionOfferingId),
    queryFn: async () => {
      const { data } = await apiClient.GET("/enrollments/roster" as never, {
        params: { query: { section_offering_id: sectionOfferingId } },
      } as never)
      return ((data as unknown) as RosterEntry[]) ?? []
    },
  })

  const unenrollMutation = useMutation({
    mutationFn: async (enrollmentId: string) => {
      await apiClient.DELETE(`/enrollments/${enrollmentId}` as never)
    },
    onSuccess: () => {
      toast.success("Student removed from section")
      qc.invalidateQueries({ queryKey: queryKeys.enrollments.roster(sectionOfferingId) })
    },
    onError: () => toast.error("Failed to remove student"),
  })

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Enrolled Students ({roster.length})</CardTitle>
        {!locked && <EnrollDialog sectionOfferingId={sectionOfferingId} roster={roster} />}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : roster.length === 0 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">
            No students enrolled yet. Use &quot;Enroll Students&quot; to add students from the registry.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Student ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                {!locked && <TableHead className="w-10" />}
              </TableRow>
            </TableHeader>
            <TableBody>
              {roster.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>{r.student_id_number}</TableCell>
                  <TableCell>{r.full_name}</TableCell>
                  <TableCell>{r.email ?? <span className="text-muted-foreground">—</span>}</TableCell>
                  {!locked && (
                    <TableCell>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => unenrollMutation.mutate(r.id)}
                        disabled={unenrollMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}
