import { apiFetch, PUBLIC_API_URL } from "@/lib/api/client"

export type ExamType = "MID" | "FINAL"

export type AuditableSection = {
  id: string
  course_code: string
  course_title: string
  section_name: string
  term_name: string
  batch_name: string
}

export type BloomLevelRef = { id: string; code: string; name: string }
export type CourseOutcomeRef = { id: string; code: string; statement: string }

export type QuestionAudit = {
  id: string
  alignment: "ALIGNED" | "PARTIAL" | "MISALIGNED" | "ABSTAINED"
  confidence: number | null
  raw_confidence: number | null
  /** Share of the independent AI judgments that agree with the result. */
  agreement: number | null
  samples: number | null
  rationale: string | null
  evidence_quote: string | null
  ai_bloom_level: BloomLevelRef | null
  ai_course_outcome: CourseOutcomeRef | null
  model: string
  prompt_version: string
  review_status: "PENDING" | "ACCEPTED" | "OVERRIDDEN"
  override_reason: string | null
  reviewed_at: string | null
  created_at: string
}

export type AuditedQuestion = {
  question_id: string
  label: string
  max_marks: number
  question_text: string | null
  declared_bloom_level: BloomLevelRef | null
  declared_course_outcome: CourseOutcomeRef | null
  audit: QuestionAudit | null
}

export type ExtractedQuestion = {
  label: string
  text: string
  context: string | null
  marks: number | null
  co: string | null
  figure: string | null
  /** Set when the wording could not be found in the uploaded document. */
  warning: string | null
  matched_question_id: string | null
}

export type QuestionPaper = {
  id: string
  exam_type: ExamType
  original_filename: string
  content_type: string
  file_size_bytes: number
  page_count: number | null
  extraction_method: "VISION" | "TEXT_LAYER" | "DOCX" | "MIXED" | null
  extraction_status: "PENDING" | "EXTRACTED" | "FAILED"
  extraction_error: string | null
  extraction_model: string | null
  extraction_prompt_version: string | null
  updated_at: string
  questions: ExtractedQuestion[]
}

export type IntegrityJob = {
  id: string
  kind: "READ_PAPER" | "AUDIT"
  status: "QUEUED" | "RUNNING" | "DONE" | "FAILED"
  progress_done: number
  progress_total: number | null
  error: string | null
  result: Record<string, number> | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export type IntegrityOverview = {
  section: AuditableSection
  exam_type: ExamType
  paper: QuestionPaper | null
  questions: AuditedQuestion[]
  summary: {
    questions: number
    with_text: number
    audited: number
    aligned: number
    partial: number
    misaligned: number
    abstained: number
    pending_review: number
  }
  /** The latest background job (reading or auditing) for this exam. */
  job: IntegrityJob | null
}

const API = `${PUBLIC_API_URL}/api/v1/integrity`

export const ACCEPTED_PAPER_FILES =
  "application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,image/jpeg,image/png,image/webp"

// Uploads can be large; the AI work itself runs in the background.
const UPLOAD_TIMEOUT_MS = 120_000

export function isJobActive(job: IntegrityJob | null | undefined) {
  return job?.status === "QUEUED" || job?.status === "RUNNING"
}

async function readJson<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const response = await apiFetch(`${API}${path}`, init)
  return response.json() as Promise<T>
}

function jsonBody(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
}

export const integrityApi = {
  sections: () => readJson<AuditableSection[]>("/sections"),

  overview: (sectionId: string, examType: ExamType) =>
    readJson<IntegrityOverview>(`/sections/${sectionId}?exam_type=${examType}`),

  uploadPaper: (sectionId: string, examType: ExamType, file: File) => {
    const form = new FormData()
    form.append("file", file)
    return readJson<IntegrityOverview>(`/sections/${sectionId}/paper?exam_type=${examType}`, {
      method: "POST",
      body: form,
      timeoutMs: UPLOAD_TIMEOUT_MS,
    })
  },

  saveQuestionTexts: (
    sectionId: string,
    examType: ExamType,
    items: { question_id: string; question_text: string | null }[],
  ) =>
    readJson<IntegrityOverview>(
      `/sections/${sectionId}/question-texts?exam_type=${examType}`,
      jsonBody("PUT", { items }),
    ),

  runAudit: (sectionId: string, examType: ExamType) =>
    readJson<IntegrityOverview>(`/sections/${sectionId}/audit?exam_type=${examType}`, { method: "POST" }),

  review: (auditId: string, decision: "ACCEPT" | "OVERRIDE", reason?: string) =>
    readJson<IntegrityOverview>(`/audits/${auditId}/review`, jsonBody("POST", { decision, reason })),
}

export function bloomLabel(level: BloomLevelRef | null) {
  return level ? `${level.code} ${level.name}` : "—"
}

export type COFigures = {
  max_marks: number
  average_pct: number
  students_above: number
  total_students: number
  /** Share of students at or above the threshold. */
  attained_share_pct: number
  is_attained: boolean
}

export type EvidenceQuestion = {
  question_id: string
  label: string
  exam_type: ExamType
  max_marks: number
  status: "SUPPORTED" | "CONTRADICTED" | "UNVERIFIED"
  alignment: QuestionAudit["alignment"] | null
  review_status: QuestionAudit["review_status"] | null
  ai_course_outcome: CourseOutcomeRef | null
}

export type EvidenceOutcome = {
  course_outcome: CourseOutcomeRef
  reported: COFigures
  /** null when every question mapped to this CO is contradicted by the audit. */
  evidence: COFigures | null
  verdict: "UNCHANGED" | "LOWER" | "NOT_SUPPORTED" | "NO_EVIDENCE"
  judged_marks_share: number
  questions: EvidenceQuestion[]
}

export type EvidenceAttainment = {
  section: AuditableSection
  threshold_pct: number
  total_students: number
  outcomes: EvidenceOutcome[]
  summary: {
    outcomes: number
    reported_attained: number
    evidence_attained: number
    not_supported: number
    contradicted_questions: number
    contradicted_pending_review: number
  }
}

export const evidenceApi = {
  get: (sectionId: string) => readJson<EvidenceAttainment>(`/sections/${sectionId}/evidence`),
}
