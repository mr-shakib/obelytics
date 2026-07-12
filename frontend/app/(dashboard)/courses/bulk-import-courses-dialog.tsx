"use client"

import { useRef, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  Download, Upload, FileSpreadsheet, Loader2,
  CheckCircle2, AlertCircle, Info,
} from "lucide-react"
import { getXLSX } from "@/lib/lazy-xlsx"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type BulkRow = Record<string, string | number | undefined>

type BulkImportError = { row: number; code: string; message: string }
type BulkImportResult = { created: number; errors: BulkImportError[] }

type CourseCategory = { id: string; name: string }

const COURSE_TYPE_LABELS: Record<string, string> = {
  THEORY: "Theory",
  LAB: "Lab",
  THESIS_DEFENSE: "Final Year Thesis Defense",
}

const TEMPLATE_COLUMNS = [
  "code",
  "title",
  "credits",
  "course_type",
  "course_category_name",
  "theory_hours",
  "lab_hours",
  "description",
]

const COLUMN_GUIDE: { key: string; required: boolean; description: string; example: string }[] = [
  { key: "code", required: true, description: "Unique course code (max 30 chars)", example: "CSE101" },
  { key: "title", required: true, description: "Course title (max 255 chars)", example: "Introduction to Programming" },
  { key: "credits", required: true, description: "Credit hours (0-20)", example: "3" },
  { key: "course_type", required: true, description: "One of: THEORY, LAB, THESIS_DEFENSE", example: "THEORY" },
  { key: "course_category_name", required: true, description: "Category name — must match an existing category exactly", example: "Core" },
  { key: "theory_hours", required: false, description: "Weekly theory hours (default 0)", example: "3" },
  { key: "lab_hours", required: false, description: "Weekly lab hours (default 0)", example: "0" },
  { key: "description", required: false, description: "Brief course description (optional)", example: "" },
]

async function downloadTemplate(categories: CourseCategory[]) {
  const XLSX = await getXLSX()
  const exampleCategory = categories[0]?.name ?? "Core"
  const ws = XLSX.utils.aoa_to_sheet([
    TEMPLATE_COLUMNS,
    ["CSE101", "Introduction to Programming", 3, "THEORY", exampleCategory, 3, 0, ""],
    ["CSE102", "Programming Lab", 1, "LAB", exampleCategory, 0, 2, "Hands-on lab sessions"],
    ["CSE201", "Data Structures", 3, "THEORY", exampleCategory, 3, 0, ""],
  ])
  ws["!cols"] = TEMPLATE_COLUMNS.map(() => ({ wch: 22 }))
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, "Courses")
  XLSX.writeFile(wb, "course_import_template.xlsx")
}

export function BulkImportCoursesDialog() {
  const [open, setOpen] = useState(false)
  const [rows, setRows] = useState<BulkRow[]>([])
  const [fileName, setFileName] = useState("")
  const [result, setResult] = useState<BulkImportResult | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const qc = useQueryClient()

  const { data: courseCategories = [] } = useQuery({
    queryKey: queryKeys.courseCategories.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/course-categories" as never)
      return ((data as unknown) as CourseCategory[]) ?? []
    },
    enabled: open,
  })

  const categoryNameToId = Object.fromEntries(
    courseCategories.map((c) => [c.name.toLowerCase().trim(), c.id])
  )

  async function handleFile(file: File) {
    const XLSX = await getXLSX()
    const reader = new FileReader()
    reader.onload = (e) => {
      const data = new Uint8Array(e.target?.result as ArrayBuffer)
      const wb = XLSX.read(data, { type: "array" })
      const ws = wb.Sheets[wb.SheetNames[0]]
      const parsed = XLSX.utils.sheet_to_json<BulkRow>(ws, { defval: "" })
      setRows(parsed)
      setFileName(file.name)
      setResult(null)
    }
    reader.readAsArrayBuffer(file)
  }

  function resetState() {
    setRows([])
    setFileName("")
    setResult(null)
    if (fileRef.current) fileRef.current.value = ""
  }

  const mutation = useMutation({
    mutationFn: async () => {
      const courses = rows.map((r) => {
        const categoryName = String(r["course_category_name"] ?? "").trim()
        const categoryId = categoryNameToId[categoryName.toLowerCase()]
        if (!categoryId) {
          throw new Error(`Unknown category "${categoryName}" — create it first or check spelling`)
        }
        const courseType = String(r["course_type"] ?? "").trim().toUpperCase()
        if (!COURSE_TYPE_LABELS[courseType]) {
          throw new Error(`Invalid course type "${courseType}" — must be one of: ${Object.keys(COURSE_TYPE_LABELS).join(", ")}`)
        }
        return {
          code: String(r["code"] ?? "").trim(),
          title: String(r["title"] ?? "").trim(),
          credits: Number(r["credits"] ?? 0),
          course_type: courseType,
          course_category_id: categoryId,
          theory_hours: Number(r["theory_hours"] ?? 0),
          lab_hours: Number(r["lab_hours"] ?? 0),
          description: String(r["description"] ?? "").trim() || null,
        }
      })
      const { data } = await apiClient.POST("/courses/bulk-import" as never, { body: { courses } } as never)
      return (data as unknown) as BulkImportResult
    },
    onSuccess: (res) => {
      setResult(res)
      qc.invalidateQueries({ queryKey: queryKeys.courses.all })
      if (res.errors.length === 0) {
        toast.success(`${res.created} course${res.created === 1 ? "" : "s"} created`)
      } else {
        toast.warning(`${res.created} created, ${res.errors.length} error${res.errors.length === 1 ? "" : "s"}`)
      }
    },
    onError: (err: Error) => toast.error(err.message || "Bulk import failed"),
  })

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) resetState() }}>
      <DialogTrigger render={<Button variant="outline" />}>
        <Upload className="h-4 w-4" />
        Bulk Import
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Bulk Import Courses</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-5 py-2">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">1. Download the template</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Column headers must match exactly what the importer expects.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadTemplate(courseCategories)}
              className="gap-1.5 shrink-0"
            >
              <Download className="h-3.5 w-3.5" />
              Download Template
            </Button>
          </div>

          <div>
            <p className="text-sm font-medium mb-2">2. Upload your filled-in spreadsheet</p>
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="relative flex w-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-muted-foreground/25 bg-muted/20 px-6 py-10 text-center transition-colors hover:border-muted-foreground/50 hover:bg-muted/40 cursor-pointer"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { e.preventDefault(); const file = e.dataTransfer.files[0]; if (file) handleFile(file) }}
            >
              <FileSpreadsheet className="h-10 w-10 text-muted-foreground/50" />
              <div>
                <p className="text-sm font-medium text-foreground">Drop your file here or click to browse</p>
                <p className="text-xs text-muted-foreground mt-1">Supports .xlsx, .xls, .csv</p>
              </div>
              {rows.length > 0 && (
                <Badge variant="secondary" className="mt-1">{fileName} — {rows.length} row{rows.length === 1 ? "" : "s"} loaded</Badge>
              )}
              <input
                ref={fileRef}
                type="file"
                accept=".xlsx,.xls,.csv"
                className="sr-only"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
              />
            </button>
          </div>

          {rows.length === 0 && (
            <div className="rounded-xl border bg-muted/30">
              <div className="flex items-center gap-2 px-4 py-3 text-sm font-medium">
                <Info className="h-4 w-4 text-muted-foreground" />
                How to fill in the spreadsheet
              </div>
              <div className="space-y-3 px-4 pb-4">
                <ol className="list-inside list-decimal space-y-1 text-xs text-muted-foreground">
                  <li>Open the downloaded template — it has the correct column headers and example rows.</li>
                  <li>Replace the example rows with your courses. Don&apos;t rename, reorder, or remove columns.</li>
                  <li><span className="font-mono text-foreground">code</span>, <span className="font-mono text-foreground">title</span>, <span className="font-mono text-foreground">credits</span>, <span className="font-mono text-foreground">course_type</span>, and <span className="font-mono text-foreground">course_category_name</span> are required for every row.</li>
                  <li><span className="font-mono text-foreground">course_category_name</span> must match an existing category exactly (case-insensitive). Create categories first if needed.</li>
                  <li>If a course code already exists, that row will be reported as an error (no duplicates).</li>
                  <li>Save the file as .xlsx, .xls, or .csv and upload it above.</li>
                </ol>
                <div className="overflow-auto rounded-lg border">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="whitespace-nowrap px-2 py-1.5 font-medium text-muted-foreground">Column</th>
                        <th className="whitespace-nowrap px-2 py-1.5 font-medium text-muted-foreground">Required</th>
                        <th className="px-2 py-1.5 font-medium text-muted-foreground">What to enter</th>
                        <th className="whitespace-nowrap px-2 py-1.5 font-medium text-muted-foreground">Example</th>
                      </tr>
                    </thead>
                    <tbody>
                      {COLUMN_GUIDE.map((c) => (
                        <tr key={c.key} className="border-t">
                          <td className="whitespace-nowrap px-2 py-1.5 font-mono">{c.key}</td>
                          <td className="whitespace-nowrap px-2 py-1.5">
                            {c.required
                              ? <Badge variant="secondary" className="text-[10px]">Required</Badge>
                              : <span className="text-muted-foreground">Optional</span>}
                          </td>
                          <td className="px-2 py-1.5 text-muted-foreground">{c.description}</td>
                          <td className="whitespace-nowrap px-2 py-1.5 text-muted-foreground">{c.example}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {rows.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Preview</p>
              <div className="rounded-lg border overflow-auto max-h-64">
                <table className="text-xs w-full">
                  <thead className="bg-muted/50">
                    <tr>{Object.keys(rows[0]).map((k) => <th key={k} className="px-2 py-1.5 text-left font-medium text-muted-foreground whitespace-nowrap">{k}</th>)}</tr>
                  </thead>
                  <tbody>
                    {rows.map((r, i) => (
                      <tr key={i} className="border-t">
                        {Object.keys(rows[0]).map((k) => {
                          const v = r[k]
                          return <td key={k} className="px-2 py-1.5 whitespace-nowrap max-w-[160px] truncate">{String(v ?? "")}</td>
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {result && (
            <div className="rounded-lg border p-4 space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                <span>{result.created} course{result.created === 1 ? "" : "s"} created</span>
              </div>
              {result.errors.map((e) => (
                <div key={`${e.row}-${e.code}`} className="flex items-start gap-2 text-xs text-destructive">
                  <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                  <span>Row {e.row} ({e.code || "—"}): {e.message}</span>
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <Button
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={mutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={() => mutation.mutate()}
              disabled={rows.length === 0 || mutation.isPending}
              className="gap-2 px-8"
            >
              {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              Import {rows.length > 0 ? `${rows.length} Course${rows.length === 1 ? "" : "s"}` : ""}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
