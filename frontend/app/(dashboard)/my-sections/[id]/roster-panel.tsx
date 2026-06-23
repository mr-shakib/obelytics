"use client"

import { useEffect, useRef, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, Search, Trash2, UserPlus, X, Upload, FileSpreadsheet, Download } from "lucide-react"
import * as XLSX from "xlsx"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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

export function RosterPanel({ sectionOfferingId, locked = false }: Props) {
  const qc = useQueryClient()
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [pending, setPending] = useState<Map<string, StudentSearchResult>>(new Map())
  const [bulkIds, setBulkIds] = useState<string[]>([])
  const [bulkPreview, setBulkPreview] = useState<StudentSearchResult[]>([])
  const [bulkNotFound, setBulkNotFound] = useState<string[]>([])
  const [showBulk, setShowBulk] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(t)
  }, [search])

  // ── Queries ─────────────────────────────────────────────────────────────

  const { data: roster = [], isLoading } = useQuery({
    queryKey: queryKeys.enrollments.roster(sectionOfferingId),
    queryFn: async () => {
      const { data } = await apiClient.GET("/enrollments/roster" as never, {
        params: { query: { section_offering_id: sectionOfferingId } },
      } as never)
      return ((data as unknown) as RosterEntry[]) ?? []
    },
  })

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

  const { data: allStudents = [] } = useQuery({
    queryKey: queryKeys.students.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/students" as never)
      return ((data as unknown) as StudentSearchResult[]) ?? []
    },
  })

  // ── Mutations ───────────────────────────────────────────────────────────

  const bulkEnrollMutation = useMutation({
    mutationFn: async (studentIds: string[]) => {
      const { data } = await apiClient.POST("/enrollments/bulk" as never, {
        body: { section_offering_id: sectionOfferingId, student_ids: studentIds },
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
      setBulkIds([])
      setBulkPreview([])
      setBulkNotFound([])
      setShowBulk(false)
    },
    onError: () => toast.error("Failed to enroll students"),
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

  // ── Handlers ────────────────────────────────────────────────────────────

  function togglePending(student: StudentSearchResult) {
    setPending((prev) => {
      const next = new Map(prev)
      if (next.has(student.id)) next.delete(student.id)
      else next.set(student.id, student)
      return next
    })
  }

  function handleBulkUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ""

    const reader = new FileReader()
    reader.onload = (evt) => {
      try {
        const wb = XLSX.read(evt.target?.result, { type: "array" })
        const ws = wb.Sheets[wb.SheetNames[0]]
        const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(ws)

        const ids: string[] = []
        for (const row of rows) {
          const id = String(row["Student ID"] ?? row["student_id"] ?? row["ID"] ?? Object.values(row)[0] ?? "").trim()
          if (id) ids.push(id)
        }

        if (ids.length === 0) {
          toast.error("No student IDs found in the file. Use column header 'Student ID'.")
          return
        }

        const studentByIdNumber = new Map(allStudents.map((s) => [s.student_id_number, s]))
        const found: StudentSearchResult[] = []
        const notFound: string[] = []

        for (const idNumber of ids) {
          const student = studentByIdNumber.get(idNumber)
          if (student) found.push(student)
          else notFound.push(idNumber)
        }

        setBulkIds(ids)
        setBulkPreview(found)
        setBulkNotFound(notFound)
        setShowBulk(true)
        toast.success(`Found ${found.length} of ${ids.length} students`)
      } catch {
        toast.error("Failed to parse Excel file")
      }
    }
    reader.readAsArrayBuffer(file)
  }

  function downloadTemplate() {
    const wb = XLSX.utils.book_new()
    const ws = XLSX.utils.aoa_to_sheet([["Student ID"], ["2021-1-60-001"], ["2021-1-60-002"]])
    ws["!cols"] = [{ wch: 20 }]
    XLSX.utils.book_append_sheet(wb, ws, "Students")
    XLSX.writeFile(wb, "enrollment_template.xlsx")
  }

  const allPendingIds = showBulk
    ? bulkPreview.map((s) => s.id)
    : Array.from(pending.keys())

  const canEnroll = allPendingIds.length > 0

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Available students */}
        <Card className="flex flex-col">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Add Students</CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={downloadTemplate}>
                  <Download className="h-3.5 w-3.5" />
                  Template
                </Button>
                <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
                  <Upload className="h-3.5 w-3.5" />
                  Bulk Import
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  className="hidden"
                  onChange={handleBulkUpload}
                />
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col gap-3">
            {!showBulk ? (
              <>
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    className="pl-8"
                    placeholder="Search by ID or name…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </div>
                <div className="flex-1 max-h-[400px] overflow-y-auto rounded-md border">
                  {isFetching ? (
                    <div className="flex justify-center py-6">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    </div>
                  ) : debouncedSearch.length === 0 ? (
                    <p className="py-6 text-center text-sm text-muted-foreground">
                      Search or use Bulk Import to add students.
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
                              <span className="font-mono text-xs text-muted-foreground">{s.student_id_number}</span>
                              <span className="ml-2 font-medium">{s.full_name}</span>
                            </div>
                            <Button
                              size="sm"
                              variant={isPending ? "secondary" : "outline"}
                              disabled={alreadyEnrolled}
                              onClick={() => togglePending(s)}
                            >
                              {alreadyEnrolled ? "Enrolled" : isPending ? "Added" : "Add"}
                            </Button>
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">
                    <FileSpreadsheet className="inline h-4 w-4 mr-1" />
                    Bulk Import — {bulkPreview.length} found, {bulkNotFound.length} not found
                  </p>
                  <Button variant="ghost" size="sm" onClick={() => { setShowBulk(false); setBulkIds([]); setBulkPreview([]); setBulkNotFound([]) }}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
                {bulkNotFound.length > 0 && (
                  <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs">
                    <p className="font-medium text-destructive mb-1">Not found in registry:</p>
                    <p className="text-muted-foreground">{bulkNotFound.join(", ")}</p>
                  </div>
                )}
                <div className="max-h-[350px] overflow-y-auto rounded-md border">
                  {bulkPreview.length === 0 ? (
                    <p className="py-6 text-center text-sm text-muted-foreground">No matching students found.</p>
                  ) : (
                    <ul className="divide-y">
                      {bulkPreview.map((s) => {
                        const alreadyEnrolled = enrolledIds.has(s.id)
                        return (
                          <li key={s.id} className="flex items-center justify-between px-3 py-2 text-sm">
                            <div>
                              <span className="font-mono text-xs text-muted-foreground">{s.student_id_number}</span>
                              <span className="ml-2 font-medium">{s.full_name}</span>
                            </div>
                            {alreadyEnrolled && <Badge variant="secondary">Enrolled</Badge>}
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right: Currently enrolled */}
        <Card className="flex flex-col">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Enrolled Students ({roster.length})</CardTitle>
          </CardHeader>
          <CardContent className="flex-1">
            {isLoading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : roster.length === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">
                No students enrolled yet.
              </p>
            ) : (
              <div className="max-h-[400px] overflow-y-auto rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Student ID</TableHead>
                      <TableHead>Name</TableHead>
                      {!locked && <TableHead className="w-10" />}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {roster.map((r) => (
                      <TableRow key={r.id}>
                        <TableCell className="font-mono text-xs">{r.student_id_number}</TableCell>
                        <TableCell>{r.full_name}</TableCell>
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
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Sticky save button */}
      {canEnroll && (
        <div className="sticky bottom-0 z-10 -mx-4 -mb-4 border-t bg-background px-4 py-3 flex items-center justify-between rounded-b-lg shadow-[0_-2px_8px_rgba(0,0,0,0.08)]">
          <p className="text-sm text-muted-foreground">
            {allPendingIds.length} student{allPendingIds.length === 1 ? "" : "s"} ready to enroll
          </p>
          <Button
            onClick={() => bulkEnrollMutation.mutate(allPendingIds)}
            disabled={bulkEnrollMutation.isPending}
          >
            {bulkEnrollMutation.isPending && <Loader2 className="animate-spin" />}
            <UserPlus className="h-4 w-4" />
            Enroll {allPendingIds.length} Student{allPendingIds.length === 1 ? "" : "s"}
          </Button>
        </div>
      )}
    </div>
  )
}
