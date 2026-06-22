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
  Info, ChevronDown,
} from "lucide-react"
import { useRouter, useSearchParams } from "next/navigation"
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

const FACULTY_TYPES = ["Faculty", "Administrative", "Management"] as const
const TITLES = ["Dr.", "Mr.", "Ms.", "Prof.", "Assoc. Prof."] as const
const DESIGNATIONS = [
  "Professor", "Associate Professor", "Assistant Professor",
  "Senior Lecturer", "Lecturer", "Head of Department",
  "Director", "Administrative Officer",
] as const
const SCOPE_TYPES = ["GLOBAL", "PROGRAM"] as const

// Each column: key (field name), display (plain Excel header), required, description, example
const BULK_COLUMN_GUIDE: {
  key: string
  display: string
  required: boolean
  description: string
  example: string
}[] = [
  { key: "first_name",       display: "First Name",        required: true,  description: "User's first name",                                                             example: "John"                 },
  { key: "last_name",        display: "Last Name",         required: false, description: "User's last name",                                                              example: "Smith"                },
  { key: "title",            display: "Title",             required: false, description: "Honorific — e.g. Dr., Mr., Ms., Prof., Assoc. Prof.",                          example: "Dr."                  },
  { key: "employee_id",      display: "Employee ID",       required: true,  description: "Unique employee or faculty ID assigned by the institution",                     example: "EMP-2024-001"         },
  { key: "faculty_type",     display: "Faculty Type",      required: false, description: "Faculty category — Faculty, Administrative, or Management",                    example: "Faculty"              },
  { key: "email",            display: "Email",             required: true,  description: "Valid, unique email address — this becomes the user's login",                  example: "john.smith@university.edu" },
  { key: "contact_number",   display: "Contact Number",    required: false, description: "Phone number, including country code if applicable",                           example: "+8801XXXXXXXXX"       },
  { key: "nid",              display: "NID",               required: false, description: "National ID number",                                                            example: "1234567890"           },
  { key: "designation",      display: "Designation",       required: false, description: "Job title — e.g. Professor, Lecturer, Head of Department",                    example: "Lecturer"             },
  { key: "department_name",  display: "Department",        required: false, description: "Must exactly match an existing department's name (case-insensitive)",          example: "Computer Science"     },
  { key: "qualification",    display: "Qualification",     required: false, description: "Highest academic qualification",                                               example: "PhD"                  },
  { key: "experience_years", display: "Experience (Years)",required: false, description: "Whole number from 0 to 99",                                                    example: "5"                    },
  { key: "password",         display: "Password",          required: false, description: "At least 8 characters; leave blank to use the default password set on the import screen", example: "(leave blank)" },
]

// Map from plain display name → field key for reading uploaded files
const DISPLAY_TO_KEY = Object.fromEntries(BULK_COLUMN_GUIDE.map((c) => [c.display, c.key]))

// ── Schema ─────────────────────────────────────────────────────────────────────

const schema = z
  .object({
    faculty_type: z.string().min(1, "Required"),
    title: z.string().optional(),
    first_name: z.string().min(1, "Required"),
    last_name: z.string().optional(),
    employee_id: z.string().min(1, "Required"),
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
          middle_name: null,
          last_name: values.last_name || null,
          title: values.title || null,
          employee_id: values.employee_id,
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
      const parts = [values.title, values.first_name, values.last_name].filter(Boolean)
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
      className="flex flex-col gap-6"
    >
      {/* Personal Information */}
      <div className="space-y-4">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Personal Information</p>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Title">
            <Select value={selTitle} onValueChange={(v) => { if (v == null) return; setSelTitle(v as string); setValue("title", v as string) }}>
              <SelectTrigger className="w-full"><SelectValue placeholder="Select title" /></SelectTrigger>
              <SelectContent>{TITLES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
          <Field label="Faculty Type" required error={errors.faculty_type?.message}>
            <Select value={selFacultyType} onValueChange={(v) => { if (v == null) return; setSelFacultyType(v as string); setValue("faculty_type", v as string, { shouldValidate: true }) }}>
              <SelectTrigger className="w-full"><SelectValue placeholder="Select type" /></SelectTrigger>
              <SelectContent>{FACULTY_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="First Name" required error={errors.first_name?.message}>
            <Input placeholder="First name" {...register("first_name")} />
          </Field>
          <Field label="Last Name" error={errors.last_name?.message}>
            <Input placeholder="Last name" {...register("last_name")} />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Employee ID" required error={errors.employee_id?.message}>
            <Input placeholder="e.g. EMP-2024-001" {...register("employee_id")} />
          </Field>
          <Field label="Email" required error={errors.email?.message}>
            <Input type="email" placeholder="name@university.edu" {...register("email")} />
          </Field>
        </div>
      </div>

      {/* Professional Information */}
      <div className="space-y-4">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Professional Information</p>
        <div className="grid grid-cols-2 gap-4">
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
          <Field label="Designation" error={errors.designation?.message}>
            <Select value={selDesignation} onValueChange={(v) => { if (v == null) return; setSelDesignation(v as string); setValue("designation", v as string) }}>
              <SelectTrigger className="w-full"><SelectValue placeholder="Select designation" /></SelectTrigger>
              <SelectContent>{DESIGNATIONS.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Highest Qualification" error={errors.qualification?.message}>
            <Input placeholder="e.g. PhD, MSc, MBA" {...register("qualification")} />
          </Field>
          <Field label="Experience (Years)" error={errors.experience_years?.message}>
            <Input type="number" min={0} max={99} placeholder="0" {...register("experience_years")} />
          </Field>
        </div>
      </div>

      {/* Contact Information */}
      <div className="space-y-4">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Contact Information</p>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Contact Number" error={errors.contact_number?.message}>
            <Input placeholder="+880 ..." {...register("contact_number")} />
          </Field>
          <Field label="NID" error={errors.nid?.message}>
            <Input placeholder="National ID number" {...register("nid")} />
          </Field>
        </div>
      </div>

      {/* Access & Permissions */}
      <div className="space-y-4">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Access & Permissions</p>
        <div className="grid grid-cols-2 gap-4">
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
          <Field label="Scope" required>
            <Select value={selScopeType} onValueChange={(v) => { if (v == null) return; const val = v as "GLOBAL" | "PROGRAM"; setSelScopeType(val); setValue("scope_type", val, { shouldValidate: true }); setSelScopeId(""); setValue("scope_id", undefined) }}>
              <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
              <SelectContent>{SCOPE_TYPES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
        </div>
        {selScopeType === "PROGRAM" && (
          <div className="grid grid-cols-2 gap-4">
            <div />
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
          </div>
        )}
      </div>

      {/* Password */}
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

function BulkImportPanel({ departments }: { departments: Department[] }) {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)

  const [rows, setRows] = useState<BulkRow[]>([])
  const [sharedPassword, setSharedPassword] = useState(() => genPassword())
  const [importResult, setImportResult] = useState<{ created: number; errors: { row: number; email: string; error: string }[] } | null>(null)

  const deptByName = Object.fromEntries(departments.map((d) => [d.name.toLowerCase(), d.id]))

  // Normalize a parsed row: accepts both display names ("First Name") and field keys ("first_name")
  function normalizeRow(raw: BulkRow): BulkRow {
    const out: BulkRow = {}
    for (const [k, v] of Object.entries(raw)) {
      const mapped = DISPLAY_TO_KEY[k] ?? k
      out[mapped] = v
    }
    return out
  }

  function handleFile(file: File) {
    const reader = new FileReader()
    reader.onload = (e) => {
      const data = new Uint8Array(e.target?.result as ArrayBuffer)
      const wb = XLSX.read(data, { type: "array" })
      const ws = wb.Sheets[wb.SheetNames[0]]
      const parsed = XLSX.utils.sheet_to_json<BulkRow>(ws, { defval: "" })
      setRows(parsed.slice(0, 200).map(normalizeRow))
      setImportResult(null)
    }
    reader.readAsArrayBuffer(file)
  }

  function downloadTemplate() {
    const wb = XLSX.utils.book_new()
    const ws: XLSX.WorkSheet = {}

    // Required columns get a red header; optional columns get a blue-grey header
    const RED_FILL   = { patternType: "solid", fgColor: { rgb: "FFC0392B" } }
    const BLUE_FILL  = { patternType: "solid", fgColor: { rgb: "FF2C3E50" } }
    const WHITE_FONT = { bold: true, color: { rgb: "FFFFFFFF" }, sz: 11 }

    BULK_COLUMN_GUIDE.forEach((col, idx) => {
      const ref = XLSX.utils.encode_cell({ r: 0, c: idx })
      ws[ref] = {
        v: col.display,
        t: "s",
        s: {
          fill: col.required ? RED_FILL : BLUE_FILL,
          font: WHITE_FONT,
          alignment: { horizontal: "center", vertical: "center", wrapText: false },
          border: {
            bottom: { style: "thin", color: { rgb: "FFFFFFFF" } },
          },
        },
      }
    })

    ws["!ref"] = XLSX.utils.encode_range({ s: { r: 0, c: 0 }, e: { r: 0, c: BULK_COLUMN_GUIDE.length - 1 } })
    ws["!cols"] = BULK_COLUMN_GUIDE.map((c) => ({ wch: Math.max(c.display.length + 4, 18) }))
    ws["!rows"] = [{ hpt: 22 }]

    XLSX.utils.book_append_sheet(wb, ws, "Users")
    XLSX.writeFile(wb, "user_import_template.xlsx", { cellStyles: true })
  }

  const mutation = useMutation({
    mutationFn: async () => {
      if (sharedPassword.trim().length < 8) throw new Error("Password must be at least 8 characters")
      const body = rows.map((r) => {
        const deptName = String(r["department_name"] ?? "").toLowerCase()
        const deptId = deptByName[deptName] ?? undefined
        const rowPassword = String(r["password"] ?? "").trim()
        const pw = rowPassword || sharedPassword
        return {
          first_name: String(r["first_name"] ?? ""),
          middle_name: String(r["middle_name"] ?? "") || null,
          last_name: String(r["last_name"] ?? "") || null,
          title: String(r["title"] ?? "") || null,
          employee_id: String(r["employee_id"] ?? ""),
          faculty_type: String(r["faculty_type"] ?? "") || null,
          email: String(r["email"] ?? ""),
          contact_number: String(r["contact_number"] ?? "") || null,
          nid: String(r["nid"] ?? "") || null,
          designation: String(r["designation"] ?? "") || null,
          department_id: deptId ?? null,
          qualification: String(r["qualification"] ?? "") || null,
          experience_years: r["experience_years"] ? Number(r["experience_years"]) : null,
          password: pw,
          role_id: null,
          scope_type: "GLOBAL",
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

  // ── Render ──────────────────────────────────────────────────────────────────

  if (rows.length > 0) {
    return (
      <div className="flex flex-col gap-5">
        {/* File loaded header */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">{rows.length} users ready to import</p>
            <p className="text-xs text-muted-foreground mt-0.5">Review the list below, then click Import.</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 shrink-0"
            onClick={() => { setRows([]); setImportResult(null); setTimeout(() => fileRef.current?.click(), 50) }}
          >
            <FileSpreadsheet className="h-3.5 w-3.5" />
            Change file
          </Button>
        </div>

        {/* Scrollable user list */}
        <div className="rounded-xl border overflow-hidden">
          <div className="overflow-y-auto max-h-[480px]">
            <table className="w-full text-sm border-collapse">
              <thead className="sticky top-0 z-10 bg-muted/80 backdrop-blur border-b">
                <tr>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-muted-foreground w-8">#</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-muted-foreground">Name</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-muted-foreground">Employee ID</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-muted-foreground">Email</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-muted-foreground">Designation</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-muted-foreground">Contact</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => {
                  const nameParts = [r["title"], r["first_name"], r["last_name"]].filter(Boolean)
                  const fullName = nameParts.join(" ") || "—"
                  const email = String(r["email"] ?? "")
                  const empId = String(r["employee_id"] ?? "")
                  const desig = String(r["designation"] ?? "") || "—"
                  const phone = String(r["contact_number"] ?? "") || "—"
                  const missingRequired = !email || !empId || !r["first_name"]
                  return (
                    <tr
                      key={i}
                      className={`border-b last:border-b-0 ${missingRequired ? "bg-destructive/5" : i % 2 === 0 ? "" : "bg-muted/20"}`}
                    >
                      <td className="px-3 py-2 text-xs text-muted-foreground">{i + 1}</td>
                      <td className="px-3 py-2">
                        <span className={`text-sm font-medium ${missingRequired ? "text-destructive" : ""}`}>{fullName}</span>
                      </td>
                      <td className="px-3 py-2 text-xs font-mono text-muted-foreground">{empId || <span className="text-destructive">missing</span>}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">{email || <span className="text-destructive">missing</span>}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">{desig}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">{phone}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Password */}
        <div className="rounded-xl border bg-muted/30 p-4 space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Initial Password</p>
          <Field label="Password" required>
            <div className="flex gap-2">
              <Input
                className="font-mono flex-1"
                value={sharedPassword}
                onChange={(e) => setSharedPassword(e.target.value)}
              />
              <Button type="button" variant="outline" size="icon" title="Regenerate password" onClick={() => setSharedPassword(genPassword())}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </Field>
          <p className="text-xs text-muted-foreground">
            Applied to every user — unless a row provides its own value in the Password column.
          </p>
        </div>

        {/* Import result */}
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
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending} className="gap-2 px-8">
            {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            Import {rows.length} Users
          </Button>
        </div>

        <input
          ref={fileRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          className="sr-only"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
        />
      </div>
    )
  }

  // ── Upload state ─────────────────────────────────────────────────────────────

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

      <details className="group rounded-xl border bg-muted/30">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3 text-sm font-medium [&::-webkit-details-marker]:hidden">
          <span className="flex items-center gap-2">
            <Info className="h-4 w-4 text-muted-foreground" />
            How to format your spreadsheet
          </span>
          <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-180" />
        </summary>
        <div className="space-y-3 px-4 pb-4">
          <ol className="list-inside list-decimal space-y-1 text-xs text-muted-foreground">
            <li>Click <span className="font-medium text-foreground">Template</span> to download a spreadsheet with the correct column headers.</li>
            <li>Add one row per user below the header row — don&apos;t rename, reorder, or remove columns.</li>
            <li>Columns with a <span className="font-medium text-destructive">red header</span> are required for every row; grey columns are optional.</li>
            <li>The <span className="font-medium text-foreground">Password</span> set on the next screen applies to every imported user — unless a row provides its own value in the Password column.</li>
            <li>Roles can be assigned to users after import from the user detail page.</li>
            <li>Save as .xlsx, .xls, or .csv and upload it (maximum 200 rows per import).</li>
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
                {BULK_COLUMN_GUIDE.map((c) => (
                  <tr key={c.key} className="border-t">
                    <td className="whitespace-nowrap px-2 py-1.5 font-medium">{c.display}</td>
                    <td className="whitespace-nowrap px-2 py-1.5">
                      {c.required
                        ? <Badge variant="destructive" className="text-[10px]">Required</Badge>
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
      </details>

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
        <input
          ref={fileRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          className="sr-only"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
        />
      </button>
    </div>
  )
}

// ── Main Page Component ────────────────────────────────────────────────────────

export function AddUserClient() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const initialTab = searchParams.get("tab") === "bulk" ? "bulk" : "individual"
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
      <Tabs defaultValue={initialTab}>
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
          <BulkImportPanel departments={departments} />
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
