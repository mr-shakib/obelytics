export const queryKeys = {
  // Auth
  me: ["me"] as const,

  // Organization
  org: { all: ["org"] as const },
  departments: {
    all: ["departments"] as const,
    list: (filters?: Record<string, unknown>) => ["departments", "list", filters] as const,
    detail: (id: string) => ["departments", id] as const,
  },
  programs: {
    all: ["programs"] as const,
    list: (filters?: Record<string, unknown>) => ["programs", "list", filters] as const,
    detail: (id: string) => ["programs", id] as const,
  },

  // IAM
  users: {
    all: ["users"] as const,
    list: (filters?: Record<string, unknown>) => ["users", "list", filters] as const,
    detail: (id: string) => ["users", id] as const,
    roles: (id: string) => ["users", id, "roles"] as const,
  },
  roles: {
    all: ["roles"] as const,
    list: () => ["roles", "list"] as const,
    detail: (id: string) => ["roles", id] as const,
  },

  // Reference Data
  refData: {
    bloomDomains: ["ref-data", "bloom-domains"] as const,
    assessmentTypes: ["ref-data", "assessment-types"] as const,
    poTypes: ["ref-data", "po-types"] as const,
    complexProblems: ["ref-data", "complex-problems"] as const,
    complexActivities: ["ref-data", "complex-activities"] as const,
    knowledgeProfiles: ["ref-data", "knowledge-profiles"] as const,
    all: ["ref-data"] as const,
  },

  // Curriculum
  curricula: {
    all: ["curricula"] as const,
    list: (filters?: Record<string, unknown>) => ["curricula", "list", filters] as const,
    detail: (id: string) => ["curricula", id] as const,
  },
  courses: {
    all: ["courses"] as const,
    list: (filters?: Record<string, unknown>) => ["courses", "list", filters] as const,
    detail: (id: string) => ["courses", id] as const,
  },
  batches: {
    all: ["batches"] as const,
    list: (filters?: Record<string, unknown>) => ["batches", "list", filters] as const,
    detail: (id: string) => ["batches", id] as const,
  },
  academicTerms: {
    all: ["academic-terms"] as const,
    list: (filters?: Record<string, unknown>) => ["academic-terms", "list", filters] as const,
  },
  sectionOfferings: {
    all: ["section-offerings"] as const,
    list: (filters?: Record<string, unknown>) => ["section-offerings", "list", filters] as const,
    detail: (id: string) => ["section-offerings", id] as const,
    faculty: (id: string) => ["section-offerings", id, "faculty"] as const,
    students: (id: string) => ["section-offerings", id, "students"] as const,
    assessments: (id: string) => ["section-offerings", id, "assessments"] as const,
  },

  // OBE
  programOutcomes: {
    all: ["program-outcomes"] as const,
    list: (filters?: Record<string, unknown>) => ["program-outcomes", "list", filters] as const,
    detail: (id: string) => ["program-outcomes", id] as const,
  },
  courseOutcomes: {
    all: ["course-outcomes"] as const,
    list: (curriculumId?: string, courseId?: string) =>
      ["course-outcomes", "list", curriculumId, courseId] as const,
    detail: (id: string) => ["course-outcomes", id] as const,
    mappings: (id: string) => ["course-outcomes", id, "mappings"] as const,
  },
  coPoMappings: {
    all: ["co-po-mappings"] as const,
    list: (filters?: Record<string, unknown>) => ["co-po-mappings", "list", filters] as const,
    detail: (id: string) => ["co-po-mappings", id] as const,
    entries: (id: string) => ["co-po-mappings", id, "entries"] as const,
  },

  // Assessment
  assessments: {
    all: ["assessments"] as const,
    list: (filters?: Record<string, unknown>) => ["assessments", "list", filters] as const,
    detail: (id: string) => ["assessments", id] as const,
  },
  marks: {
    byAssessment: (assessmentId: string) => ["marks", "assessment", assessmentId] as const,
    byEnrollment: (enrollmentId: string) => ["marks", "enrollment", enrollmentId] as const,
  },
  results: {
    all: ["results"] as const,
    byOffering: (offeringId: string) => ["results", "offering", offeringId] as const,
  },

  // Attainment
  attainment: {
    all: ["attainment"] as const,
    list: (filters?: Record<string, unknown>) => ["attainment", "list", filters] as const,
    run: (id: string) => ["attainment", "run", id] as const,
    trends: (programId: string) => ["attainment", "trends", programId] as const,
  },

  // Approvals
  approvals: {
    inbox: ["approvals", "inbox"] as const,
    detail: (id: string) => ["approvals", id] as const,
  },

  // Reports
  reports: {
    definitions: ["reports", "definitions"] as const,
    runs: (filters?: Record<string, unknown>) => ["reports", "runs", filters] as const,
    run: (id: string) => ["reports", "run", id] as const,
  },

  // Accreditation
  accreditation: {
    all: ["accreditation"] as const,
    list: () => ["accreditation", "list"] as const,
    cycle: (id: string) => ["accreditation", "cycle", id] as const,
  },

  // Audit
  audit: {
    logs: (filters?: Record<string, unknown>) => ["audit", "logs", filters] as const,
  },

  // Notifications
  notifications: {
    inbox: (filters?: Record<string, unknown>) => ["notifications", "inbox", filters] as const,
    unreadCount: ["notifications", "unread-count"] as const,
  },
}
