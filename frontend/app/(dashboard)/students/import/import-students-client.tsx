"use client"

import { useRef, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { useRouter } from "next/navigation"
import {
  ArrowLeft, Download, Upload, FileSpreadsheet, Loader2,
  CheckCircle2, AlertCircle, Info,
} from "lucide-react"
import * as XLSX from "xlsx"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type BulkRow = Record<string, string | number | undefined>

type BulkImportError = { row: number; student_id_number: string; message: string }
type BulkImportResult = { created: number; updated: number; errors: BulkImportError[] }

const TEMPLATE_COLUMNS = ["student_id_number", "full_name", "email"]

const COLUMN_GUIDE: { key: string; required: boolean; description: string; example: string }[] = [
  { key: "student_id_number", required: true, description: "Unique student ID / roll number", example: "221-15-1234" },
  { key: "full_name", required: true, description: "Student's full name", example: "Jane Doe" },
  { key: "email", required: false, description: "Student's email address — leave blank if not available", example: "jane@example.com" },
]

function downloadTemplate() {
  const ws = XLSX.utils.aoa_to_sheet([
    TEMPLATE_COLUMNS,
    ["221-15-1234", "Jane Doe", "jane@example.com"],
    ["221-15-1235", "John Smith", ""],
  ])
  ws["!cols"] = TEMPLATE_COLUMNS.map(() => ({ wch: 20 }))
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, "Students")
  XLSX.writeFile(wb, "student_import_template.xlsx")
}

export function ImportStudentsClient() {
  const router = useRouter()
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)

  const [rows, setRows] = useState<BulkRow[]>([])
  const [fileName, setFileName] = useState("")
  const [result, setResult] = useState<BulkImportResult | null>(null)

  function handleFile(file: File) {
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

  const mutation = useMutation({
    mutationFn: async () => {
      const body = {
        students: rows.map((r) => ({
          student_id_number: String(r["student_id_number"] ?? "").trim(),
          full_name: String(r["full_name"] ?? "").trim(),
          email: String(r["email"] ?? "").trim() || null,
        })),
      }
      const { data } = await apiClient.POST("/students/bulk-import" as never, { body } as never)
      return (data as unknown) as BulkImportResult
    },
    onSuccess: (res) => {
      setResult(res)
      qc.invalidateQueries({ queryKey: queryKeys.students.all })
      if (res.errors.length === 0) {
        toast.success(`${res.created} created, ${res.updated} updated`)
      } else {
        toast.warning(`${res.created} created, ${res.updated} updated, ${res.errors.length} error${res.errors.length === 1 ? "" : "s"}`)
      }
    },
    onError: () => toast.error("Bulk import failed"),
  })

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <div className="mb-8">
        <button
          onClick={() => router.push("/students")}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Students
        </button>
        <h1 className="text-2xl font-semibold">Bulk Import Students</h1>
        <p className="text-muted-foreground mt-1">
          Add many students to the registry at once by uploading a filled-in spreadsheet.
        </p>
      </div>

      <div className="flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">1. Download the template</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Use this spreadsheet so the column headers match exactly what the importer expects.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={downloadTemplate} className="gap-1.5 shrink-0">
            <Download className="h-3.5 w-3.5" />
            Download Template
          </Button>
        </div>

        <div className="rounded-xl border bg-muted/30">
          <div className="flex items-center gap-2 px-4 py-3 text-sm font-medium">
            <Info className="h-4 w-4 text-muted-foreground" />
            How to fill in the spreadsheet
          </div>
          <div className="space-y-3 px-4 pb-4">
            <ol className="list-inside list-decimal space-y-1 text-xs text-muted-foreground">
              <li>Open the downloaded template — it already has the correct column headers and two example rows.</li>
              <li>Replace the example rows with your students, one row per student. Don&apos;t rename, reorder, or remove columns.</li>
              <li><span className="font-mono text-foreground">student_id_number</span> and <span className="font-mono text-foreground">full_name</span> are required for every row.</li>
              <li><span className="font-mono text-foreground">email</span> is optional — leave it blank if a student doesn&apos;t have one.</li>
              <li>If a student ID already exists in the system, that student&apos;s name/email will be updated instead of creating a duplicate.</li>
              <li>Save the file as .xlsx, .xls, or .csv and upload it below.</li>
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

        {rows.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Preview — first 5 rows</p>
            <div className="rounded-lg border overflow-auto max-h-48">
              <table className="text-xs w-full">
                <thead className="bg-muted/50">
                  <tr>{Object.keys(rows[0]).map((k) => <th key={k} className="px-2 py-1.5 text-left font-medium text-muted-foreground whitespace-nowrap">{k}</th>)}</tr>
                </thead>
                <tbody>
                  {rows.slice(0, 5).map((r, i) => (
                    <tr key={i} className="border-t">
                      {Object.values(r).map((v, j) => <td key={j} className="px-2 py-1.5 whitespace-nowrap max-w-[160px] truncate">{String(v)}</td>)}
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
              <span>{result.created} created, {result.updated} updated</span>
            </div>
            {result.errors.map((e) => (
              <div key={`${e.row}-${e.student_id_number}`} className="flex items-start gap-2 text-xs text-destructive">
                <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                <span>Row {e.row} ({e.student_id_number || "—"}): {e.message}</span>
              </div>
            ))}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <Button onClick={() => mutation.mutate()} disabled={rows.length === 0 || mutation.isPending} className="gap-2 px-8">
            {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            Import {rows.length > 0 ? `${rows.length} Student${rows.length === 1 ? "" : "s"}` : ""}
          </Button>
        </div>
      </div>
    </div>
  )
}
