export type ModuleLeaderAssignment = {
  id: string
  batch_id: string
  academic_term_id: string
  course_id: string
  user_id: string
}

export type Course = {
  id: string
  code: string
  title: string
  credits: number
  course_category_id: string
  course_type: string
  theory_hours: number
  lab_hours: number
  description: string | null
  syllabus_content: string | null
  status: string
}

export type CourseCategory = { id: string; name: string }

export type BloomDomain = { id: string; name: string }

export type BloomLevel = { id: string; code: string; name: string; bloom_domain_id: string; order_index: number }

export type AssessmentType = { id: string; name: string; is_sessional: boolean }

export type CourseAssessmentTool = {
  id: string
  assessment_type_id: string
  assessment_type_name: string
  is_sessional: boolean
  is_locked: boolean
}

export type CourseObjective = { id: string; order_index: number; statement: string }

export type CourseLearningMaterial = {
  id: string
  material_type: "TEXTBOOK" | "REFERENCE"
  order_index: number
  title: string
  authors: string | null
  publisher: string | null
  edition_year: string | null
}

export type LessonPlanItem = {
  id: string
  week_number: number
  lesson_label: string | null
  topic: string
  tla: string | null
  assessment_strategy: string | null
  order_index: number
  co_ids: string[]
  po_ids: string[]
}

export type CourseOutcome = { id: string; code: string; statement: string; bloom_level_ids: string[] }
export type ProgramOutcome = { id: string; code: string; statement: string }
export type CurriculumDetail = { id: string; program_id: string }

export type CourseCOMark = {
  assessment_type_id: string
  course_outcome_id: string | null
  marks: number | string
}

export type CourseBloomMark = {
  assessment_type_id: string
  bloom_level_id: string
  component: "CIE" | "SEE"
  marks: number | string
}

export type Prerequisite = { id: string; course_id: string; prerequisite_course_id: string }

export type CourseListItem = { id: string; code: string; title: string }

export const COURSE_TYPE_LABELS: Record<string, string> = {
  THEORY: "Theory",
  LAB: "Lab",
  THESIS_DEFENSE: "Final Year Thesis Defense",
}
