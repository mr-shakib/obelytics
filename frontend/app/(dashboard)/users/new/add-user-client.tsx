"use client"

import { useState, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import {
  Loader2, RefreshCw,
  FileSpreadsheet, Upload, Download, AlertCircle, CheckCircle2, ArrowLeft,
} from "lucide-react"
import { useRouter } from "next/navigation"
import * as XLSX from "xlsx"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { CredentialsDialog, genPassword, type Credentials } from "@/components/shared/credentials-dialog"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

// ── Types ──────────────────────────────────────────────────────────────────────

type Role = { id: string; name: string }
type Department = { id: string; name: string; short_name: string }
type Program = { id: string; title?: string; name?: string; acronym?: string }
type CreatedCreds = Credentials

// ── Constants ──────────────────────────────────────────────────────────────────

const FACULTY_TYPES = ["Teaching", "Administrative", "Management"] as const
const TITLES = ["Dr.", "Mr.", "Ms.", "Prof.", "Assoc. Prof."] as const
const DESIGNATIONS = [
  "Professor", "Associate Professor", "Assistant Professor",
  "Senior Lecturer", "Lecturer", "Head of Department",
  "Director", "Administrative Officer",
] as const
const SCOPE_TYPES = ["GLOBAL", "PROGRAM"] as const

const BULK_TEMPLATE_COLUMNS = [
  "first_name", "last_name", "middle_name", "title",
  "faculty_type", "email", "contact_number", "nid",
  "designation", "department_name", "qualification", "experience_years", "password",
]

// ── Schema ─────────────────────────────────────────────────────────────────────

const schema = z
  .object({
    faculty_type: z.string().min(1, "Required"),
    title: z.string().optional(),
    first_name: z.string().min(1, "Required"),
    middle_name: z.string().optional(),
    last_name: z.string().optional(),
    email: z.string().email("Invalid email"),
    contact_number: z.string().optional(),
    nid: z.string().optional(),
    department_id: z.string().optional(),
    designation: z.string().optional(),
    qualification: z.string().optional(),
    experience_years: z.string().optional(),
    role_id: z.string().min(1, "Role required"),
    scope_type: z.enum(SCOPE_TYPES),
    scope_id: z.string().optional(),
    password: z.string().min(8, "Min 8 characters"),
  })
  .superRefine((d, ctx) => {
    if (d.scope_type === "PROGRAM" && !d.scope_id)
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Program required", path: ["scope_id"] })
  })

type FormValues = z.infer<typeof schema>

// ── Field wrapper ──────────────────────────────────────────────────────────────

function Field({
  label, required, error, children,
}: { label: string; required?: boolean; error?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}{required && <span className="ml-0.5 text-destructive">*</span>}
      </Label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

// ── Individual Add Form ────────────────────────────────────────────────────────

function IndividualForm({
  roles, departments, programs, onCreated,
}: {
  roles: Role[]
  departments: Department[]
  programs: Program[]
  onCreated: (creds: CreatedCreds) => void
}) {
  const qc = useQueryClient()

  const [selFacultyType, setSelFacultyType] = useState("")
  const [selTitle, setSelTitle] = useState("")
  const [selDeptId, setSelDeptId] = useState("")
  const [selDesignation, setSelDesignation] = useState("")
  const [selRoleId, setSelRoleId] = useState("")
  const [selScopeType, setSelScopeType] = useState<"GLOBAL" | "PROGRAM">("GLOBAL")
  const [selScopeId, setSelScopeId] = useState("")
  const [password, setPassword] = useState(() => genPassword())

  const {
    register, handleSubmit, setValue, reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { scope_type: "GLOBAL", password },
  })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.POST("/users" as never, {
        body: {
          email: values.email,
          first_name: values.first_name,
          middle_name: values.middle_name || null,
          last_name: values.last_name || null,
          title: values.title || null,
          faculty_type: values.faculty_type,
          nid: values.nid || null,
          department_id: values.department_id || null,
          designation: values.designation || null,
          contact_number: values.contact_number || null,
          qualification: values.qualification || null,
          experience_years: values.experience_years ? parseInt(values.experience_years as string) : null,
          password: values.password,
          role_id: values.role_id,
          scope_type: values.scope_type,
          scope_id: values.scope_type === "PROGRAM" ? values.scope_id : null,
        },
      } as never)
      const parts = [values.title, values.first_name, values.middle_name, values.last_name].filter(Boolean)
      return { email: values.email, full_name: parts.join(" "), password: values.password }
    },
    onSuccess: (creds) => {
      qc.invalidateQueries({ queryKey: queryKeys.users.all })
      const next = genPassword()
      setPassword(next)
      reset({ scope_type: "GLOBAL", password: next })
      setSelFacultyType(""); setSelTitle(""); setSelDeptId(""); setSelDesignation("")
      setSelRoleId(""); setSelScopeType("GLOBAL"); setSelScopeId("")
      onCreated(creds)
    },
    onError: () => toast.error("Failed to create user"),
  })

  return (
    <form
      onSubmit={handleSubmit((v) => mutation.mutate(v))}
      className="flex flex-col gap-5"
    >
      <div className="grid grid-cols-2 gap-4">
        <Field label="Faculty Type" required error={errors.faculty_type?.message}>
          <Select value={selFacultyType} onValueChange={(v) => { if (v == null) return; setSelFacultyType(v as string); setValue("faculty_type", v as string, { shouldValidate: true }) }}>
            <SelectTrigger className="w-full"><SelectValue placeholder="Select type" /></SelectTrigger>
            <SelectContent>{FACULTY_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
          </Select>
        </Field>
        <Field label="NID" error={errors.nid?.message}>
          <Input placeholder="National ID number" {...register("nid")} />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Title">
          <Select value={selTitle} onValueChange={(v) => { if (v == null) return; setSelTitle(v as string); setValue("title", v as string) }}>
            <SelectTrigger className="w-full"><SelectValue placeholder="Select title" /></SelectTrigger>
            <SelectContent>{TITLES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
          </Select>
        </Field>
        <Field label="Department" error={errors.department_id?.message}>
          <Select value={selDeptId} onValueChange={(v) => { if (v == null) return; setSelDeptId(v as string); setValue("department_id", v as string) }}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select department">
                {selDeptId ? departments.find(d => d.id === selDeptId)?.name : undefined}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>{departments.map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}</SelectContent>
          </Select>
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="First Name" required error={errors.first_name?.message}>
          <Input placeholder="First name" {...register("first_name")} />
        </Field>
        <Field label="Designation" error={errors.designation?.message}>
          <Select value={selDesignation} onValueChange={(v) => { if (v == null) return; setSelDesignation(v as string); setValue("designation", v as string) }}>
            <SelectTrigger className="w-full"><SelectValue placeholder="Select designation" /></SelectTrigger>
            <SelectContent>{DESIGNATIONS.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
          </Select>
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Middle Name" error={errors.middle_name?.message}>
          <Input placeholder="Middle name" {...register("middle_name")} />
        </Field>
        <Field label="Role" required error={errors.role_id?.message}>
          <Select value={selRoleId} onValueChange={(v) => { if (v == null) return; setSelRoleId(v as string); setValue("role_id", v as string, { shouldValidate: true }) }}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select role">
                {selRoleId ? roles.find(r => r.id === selRoleId)?.name : undefined}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>{roles.map((r) => <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>)}</SelectContent>
          </Select>
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Last Name" error={errors.last_name?.message}>
          <Input placeholder="Last name" {...register("last_name")} />
        </Field>
        <Field label="Highest Qualification" error={errors.qualification?.message}>
          <Input placeholder="e.g. PhD, MSc, MBA" {...register("qualification")} />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Email" required error={errors.email?.message}>
          <Input type="email" placeholder="name@university.edu" {...register("email")} />
        </Field>
        <Field label="Experience (Years)" error={errors.experience_years?.message}>
          <Input type="number" min={0} max={99} placeholder="0" {...register("experience_years")} />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Contact Number" error={errors.contact_number?.message}>
          <Input placeholder="+880 ..." {...register("contact_number")} />
        </Field>
        <Field label="Scope" required>
          <Select value={selScopeType} onValueChange={(v) => { if (v == null) return; const val = v as "GLOBAL" | "PROGRAM"; setSelScopeType(val); setValue("scope_type", val, { shouldValidate: true }); setSelScopeId(""); setValue("scope_id", undefined) }}>
            <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>{SCOPE_TYPES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
          </Select>
        </Field>
      </div>

      {selScopeType === "PROGRAM" && (
        <Field label="Program" required error={errors.scope_id?.message}>
          <Select value={selScopeId} onValueChange={(v) => { setSelScopeId((v as string | null) ?? ""); setValue("scope_id", (v as string | null) ?? undefined, { shouldValidate: true }) }}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select program">
                {selScopeId ? (() => { const p = programs.find(p => p.id === selScopeId); return p ? (p.acronym ? `${p.acronym} — ${p.title ?? p.name ?? ""}` : p.title ?? p.name ?? "") : undefined })() : undefined}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {programs.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.acronym ? `${p.acronym} — ${p.title ?? p.name ?? ""}` : p.title ?? p.name ?? p.id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      )}

      <div className="rounded-xl border bg-muted/30 p-4 space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Initial Password</p>
        <Field label="Password" required error={errors.password?.message}>
          <div className="flex gap-2">
            <Input
              className="font-mono flex-1"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setValue("password", e.target.value, { shouldValidate: true }) }}
            />
            <Button type="button" variant="outline" size="icon" title="Regenerate password" onClick={() => { const p = genPassword(); setPassword(p); setValue("password", p, { shouldValidate: true }) }}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </Field>
        <p className="text-xs text-muted-foreground">
          Auto-generated. You can edit it or regenerate. The password will be shown after saving.
        </p>
      </div>

      <div className="flex justify-end gap-2 pt-1">
        <Button type="submit" disabled={isSubmitting || mutation.isPending} className="px-8">
          {(isSubmitting || mutation.isPending) && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
          Save User
        </Button>
      </div>
    </form>
  )
}

// ── Bulk Import Panel ──────────────────────────────────────────────────────────

type BulkRow = Record<string, string | number | undefined>

function BulkImportPanel({ roles, departments }: { roles: Role[]; departments: Department[] }) {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)

  const [rows, setRows] = useState<BulkRow[]>([])
  const [selRoleId, setSelRoleId] = useState("")
  const [selScopeType, setSelScopeType] = useState<"GLOBAL" | "PROGRAM">("GLOBAL")
  const [importResult, setImportResult] = useState<{ created: number; errors: { row: number; email: string; error: string }[] } | null>(null)

  const deptByName = Object.fromEntries(departments.map((d) => [d.name.toLowerCase(), d.id]))

  function handleFile(file: File) {
    const reader = new FileReader()
    reader.onload = (e) => {
      const data = new Uint8Array(e.target?.result as ArrayBuffer)
      const wb = XLSX.read(data, { type: "array" })
      const ws = wb.Sheets[wb.SheetNames[0]]
      const parsed = XLSX.utils.sheet_to_json<BulkRow>(ws, { defval: "" })
      setRows(parsed.slice(0, 200))
      setImportResult(null)
    }
    reader.readAsArrayBuffer(file)
  }

  function downloadTemplate() {
    const ws = XLSX.utils.aoa_to_sheet([BULK_TEMPLATE_COLUMNS])
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, "Users")
    XLSX.writeFile(wb, "user_import_template.xlsx")
  }

  const mutation = useMutation({
    mutationFn: async () => {
      if (!selRoleId) throw new Error("Select a role before importing")
      const body = rows.map((r) => {
        const deptName = String(r["department_name"] ?? "").toLowerCase()
        const deptId = deptByName[deptName] ?? undefined
        const pw = String(r["password"] ?? "").trim() || genPassword()
        return {
          first_name: String(r["first_name"] ?? ""),
          middle_name: String(r["middle_name"] ?? "") || null,
          last_name: String(r["last_name"] ?? "") || null,
          title: String(r["title"] ?? "") || null,
          faculty_type: String(r["faculty_type"] ?? "") || null,
          email: String(r["email"] ?? ""),
          contact_number: String(r["contact_number"] ?? "") || null,
          nid: String(r["nid"] ?? "") || null,
          designation: String(r["designation"] ?? "") || null,
          department_id: deptId ?? null,
          qualification: String(r["qualification"] ?? "") || null,
          experience_years: r["experience_years"] ? Number(r["experience_years"]) : null,
          password: pw,
          role_id: selRoleId,
          scope_type: selScopeType,
          scope_id: null,
        }
      })
      const { data } = await apiClient.POST("/users/bulk" as never, { body } as never)
      return (data as unknown) as { created: unknown[]; errors: { row: number; email: string; error: string }[] }
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: queryKeys.users.all })
      setImportResult({ created: result.created.length, errors: result.errors })
      if (result.errors.length === 0) {
        toast.success(`${result.created.length} users imported successfully`)
      } else {
        toast.warning(`${result.created.length} imported, ${result.errors.length} failed`)
      }
    },
    onError: (e: Error) => toast.error(e.message || "Import failed"),
  })

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium">Import from Excel / CSV</p>
          <p className="text-xs text-muted-foreground mt-0.5">Upload a spreadsheet with user data. Max 200 rows per import.</p>
        </div>
        <Button variant="outline" size="sm" onClick={downloadTemplate} className="gap-1.5 shrink-0">
          <Download className="h-3.5 w-3.5" />
          Template
        </Button>
      </div>

      <button
        type="button"
        onClick={() => fileRef.current?.click()}
        className="relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-muted-foreground/25 bg-muted/20 px-6 py-10 text-center transition-colors hover:border-muted-foreground/50 hover:bg-muted/40 cursor-pointer"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); const file = e.dataTransfer.files[0]; if (file) handleFile(file) }}
      >
        <FileSpreadsheet className="h-10 w-10 text-muted-foreground/50" />
        <div>
          <p className="text-sm font-medium text-foreground">Drop your file here or click to browse</p>
          <p className="text-xs text-muted-foreground mt-1">Supports .xlsx, .xls, .csv</p>
        </div>
        {rows.length > 0 && <Badge variant="secondary" className="mt-1">{rows.length} rows loaded</Badge>}
        <input
          ref={fileRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          className="sr-only"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
        />
      </button>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Assign Role" required>
          <Select value={selRoleId} onValueChange={(v) => { if (v != null) setSelRoleId(v as string) }}>
            <SelectTrigger className="w-full"><SelectValue placeholder="Select role for all" /></SelectTrigger>
            <SelectContent>{roles.map((r) => <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>)}</SelectContent>
          </Select>
        </Field>
        <Field label="Scope">
          <Select value={selScopeType} onValueChange={(v) => { if (v != null) setSelScopeType(v as "GLOBAL" | "PROGRAM") }}>
            <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="GLOBAL">Global</SelectItem>
              <SelectItem value="PROGRAM">Program</SelectItem>
            </SelectContent>
          </Select>
        </Field>
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
                    {Object.values(r).map((v, j) => <td key={j} className="px-2 py-1.5 whitespace-nowrap max-w-[120px] truncate">{String(v)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {importResult && (
        <div className="rounded-lg border p-4 space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
            <span>{importResult.created} users created successfully</span>
          </div>
          {importResult.errors.map((e, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-destructive">
              <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <span>Row {e.row} ({e.email}): {e.error}</span>
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-end gap-2 pt-1">
        <Button onClick={() => mutation.mutate()} disabled={rows.length === 0 || !selRoleId || mutation.isPending} className="gap-2 px-8">
          {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
          Import {rows.length > 0 ? `${rows.length} Users` : ""}
        </Button>
      </div>
    </div>
  )
}

// ── Main Page Component ────────────────────────────────────────────────────────

export function AddUserClient() {
  const router = useRouter()
  const [creds, setCreds] = useState<CreatedCreds | null>(null)

  const { data: roles = [] } = useQuery({
    queryKey: queryKeys.roles.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/roles" as never)
      return ((data as unknown) as { items?: Role[] })?.items ?? ((data as unknown) as Role[]) ?? []
    },
  })

  const { data: departments = [] } = useQuery({
    queryKey: queryKeys.departments.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/departments" as never)
      return ((data as unknown) as Department[]) ?? []
    },
  })

  const { data: programs = [] } = useQuery({
    queryKey: queryKeys.programs.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/programs" as never)
      return ((data as unknown) as Program[]) ?? []
    },
  })

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => router.push("/users")}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Users
        </button>
        <h1 className="text-2xl font-semibold">Add User</h1>
        <p className="text-muted-foreground mt-1">Add an individual user or bulk import from a spreadsheet.</p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="individual">
        <TabsList variant="line" className="mb-6">
          <TabsTrigger value="individual">Individual</TabsTrigger>
          <TabsTrigger value="bulk">Bulk Import</TabsTrigger>
        </TabsList>

        <TabsContent value="individual">
          <IndividualForm
            roles={roles}
            departments={departments}
            programs={programs}
            onCreated={(c) => setCreds(c)}
          />
        </TabsContent>

        <TabsContent value="bulk">
          <BulkImportPanel roles={roles} departments={departments} />
        </TabsContent>
      </Tabs>

      <CredentialsDialog
        creds={creds}
        onClose={() => { setCreds(null); router.push("/users") }}
        title="User Created — Share Credentials"
      />
    </div>
  )
}
