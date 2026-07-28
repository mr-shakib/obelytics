"use client"

import { useRef, useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  Download, Upload, FileSpreadsheet, Loader2,
  CheckCircle2, AlertCircle, Info,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { getXLSX } from "@/lib/lazy-xlsx"
import { exportToXlsx } from "@/lib/xlsx-export"

export type BulkUploadRow = Record<string, string | number | undefined>

export type BulkUploadError = { row: number; code: string; message: string }
export type BulkUploadResult = { created: number; errors: BulkUploadError[] }

export type BulkUploadColumn = {
  key: string
  required: boolean
  description: string
  example: string
}

export interface BulkUploadDialogProps {
  /** Singular entity name, e.g. "Knowledge Profile". */
  entityLabel: string
  /** Plural entity name used in headings, e.g. "Knowledge Profiles". */
  entityLabelPlural: string
  /** Column contract — drives the template, the guide table, and the payload. */
  columns: BulkUploadColumn[]
  /** Example rows written under the header row of the template. */
  sampleRows: (string | number)[][]
  /** Base name for the downloaded template, without extension. */
  templateFileName: string
  /** Extra bullet points appended to the standard instructions. */
  notes?: string[]
  /** Sends the parsed rows to the API and returns the per-row outcome. */
  onImport: (rows: BulkUploadRow[]) => Promise<BulkUploadResult>
  /** Called after a successful import so the caller can invalidate its queries. */
  onImported?: () => void
}

export function BulkUploadDialog({
  entityLabel,
  entityLabelPlural,
  columns,
  sampleRows,
  templateFileName,
  notes,
  onImport,
  onImported,
}: BulkUploadDialogProps) {
  const [open, setOpen] = useState(false)
  const [rows, setRows] = useState<BulkUploadRow[]>([])
  const [fileName, setFileName] = useState("")
  const [result, setResult] = useState<BulkUploadResult | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const requiredKeys = columns.filter((c) => c.required).map((c) => c.key)

  async function downloadTemplate() {
    await exportToXlsx({
      fileName: `${templateFileName}.xlsx`,
      sheetName: entityLabelPlural.slice(0, 31),
      columns: columns.map((c) => ({ key: c.key, header: c.key })),
      rows: sampleRows.map((values) =>
        Object.fromEntries(columns.map((c, i) => [c.key, values[i] ?? ""]))
      ),
    })
  }

  async function handleFile(file: File) {
    const XLSX = await getXLSX()
    const reader = new FileReader()
    reader.onload = (e) => {
      const data = new Uint8Array(e.target?.result as ArrayBuffer)
      const wb = XLSX.read(data, { type: "array" })
      const ws = wb.Sheets[wb.SheetNames[0]]
      const parsed = XLSX.utils.sheet_to_json<BulkUploadRow>(ws, { defval: "" })
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
    mutationFn: () => onImport(rows),
    onSuccess: (res) => {
      setResult(res)
      onImported?.()
      if (res.errors.length === 0) {
        toast.success(`${res.created} ${res.created === 1 ? entityLabel : entityLabelPlural} created`)
      } else {
        toast.warning(`${res.created} created, ${res.errors.length} error${res.errors.length === 1 ? "" : "s"}`)
      }
    },
    onError: (err: Error) => toast.error(err.message || "Bulk upload failed"),
  })

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) resetState() }}>
      <DialogTrigger render={<Button variant="outline" />}>
        <Upload className="h-4 w-4" />
        Bulk Upload
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Bulk Upload {entityLabelPlural}</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-5 py-2">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium">1. Download the template</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Column headers must match exactly what the importer expects.
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={downloadTemplate} className="gap-1.5 shrink-0">
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
                  <li>
                    Replace the example rows with your {entityLabelPlural.toLowerCase()}. Don&apos;t rename,
                    reorder, or remove columns.
                  </li>
                  <li>
                    {requiredKeys.map((key, i) => (
                      <span key={key}>
                        {i > 0 && (i === requiredKeys.length - 1 ? " and " : ", ")}
                        <span className="font-mono text-foreground">{key}</span>
                      </span>
                    ))}
                    {requiredKeys.length === 1 ? " is" : " are"} required for every row.
                  </li>
                  <li>Rows with a code that already exists are reported as errors — nothing is overwritten.</li>
                  {notes?.map((note) => <li key={note}>{note}</li>)}
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
                      {columns.map((c) => (
                        <tr key={c.key} className="border-t">
                          <td className="whitespace-nowrap px-2 py-1.5 font-mono">{c.key}</td>
                          <td className="whitespace-nowrap px-2 py-1.5">
                            {c.required
                              ? <Badge variant="secondary" className="text-[10px]">Required</Badge>
                              : <span className="text-muted-foreground">Optional</span>}
                          </td>
                          <td className="px-2 py-1.5 text-muted-foreground">{c.description}</td>
                          <td className="px-2 py-1.5 text-muted-foreground max-w-[220px] truncate" title={c.example}>{c.example}</td>
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
                        {Object.keys(rows[0]).map((k) => (
                          <td key={k} className="px-2 py-1.5 whitespace-nowrap max-w-[160px] truncate">{String(r[k] ?? "")}</td>
                        ))}
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
                <span>{result.created} {result.created === 1 ? entityLabel : entityLabelPlural} created</span>
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
            <Button variant="outline" onClick={() => setOpen(false)} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button
              onClick={() => mutation.mutate()}
              disabled={rows.length === 0 || mutation.isPending}
              className="gap-2 px-8"
            >
              {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              Upload {rows.length > 0 ? `${rows.length} Row${rows.length === 1 ? "" : "s"}` : ""}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
