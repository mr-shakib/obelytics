import {
  LayoutDashboard,
  Building2,
  Building,
  GraduationCap,
  Users,
  Shield,
  Database,
  BookOpen,
  BookCopy,
  Users2,
  CalendarDays,
  Layers,
  Target,
  ListChecks,
  Grid3x3,
  ClipboardList,
  BarChart3,
  Bell,
  FileText,
  Award,
  ScrollText,
  CheckSquare,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"

export interface NavItem {
  label: string
  href: string
  icon: LucideIcon
  permission: string | null
  group?: string
}

export const NAV_ITEMS: NavItem[] = [
  // Core
  { label: "Dashboard", href: "/overview", icon: LayoutDashboard, permission: null, group: "Core" },
  { label: "Approvals", href: "/approvals", icon: CheckSquare, permission: null, group: "Core" },

  // Organization & IAM
  { label: "Organization", href: "/organization", icon: Building2, permission: "system.organization.configure", group: "Administration" },
  { label: "Departments", href: "/departments", icon: Building, permission: "department.read", group: "Administration" },
  { label: "Programs", href: "/programs", icon: GraduationCap, permission: "program.read", group: "Administration" },
  { label: "Users", href: "/users", icon: Users, permission: "user.read", group: "Administration" },
  { label: "Roles", href: "/roles", icon: Shield, permission: "system.roles.create", group: "Administration" },
  { label: "Reference Data", href: "/ref-data", icon: Database, permission: "config.bloom.manage", group: "Administration" },

  // Curriculum
  { label: "Curricula", href: "/curricula", icon: BookCopy, permission: "curriculum.read", group: "Curriculum" },
  { label: "Courses", href: "/courses", icon: BookOpen, permission: "course.read", group: "Curriculum" },
  { label: "Batches", href: "/batches", icon: Users2, permission: "batch.read", group: "Curriculum" },
  { label: "Academic Terms", href: "/academic-terms", icon: CalendarDays, permission: "curriculum.read", group: "Curriculum" },
  { label: "Section Offerings", href: "/section-offerings", icon: Layers, permission: "curriculum.read", group: "Curriculum" },

  // OBE
  { label: "Program Outcomes", href: "/program-outcomes", icon: Target, permission: "po.read", group: "OBE" },
  { label: "Course Outcomes", href: "/course-outcomes", icon: ListChecks, permission: "co.read", group: "OBE" },
  { label: "CO-PO Mapping", href: "/mappings/co-po", icon: Grid3x3, permission: "mapping.co_po.read", group: "OBE" },

  // Assessment
  { label: "Assessments", href: "/assessments", icon: ClipboardList, permission: "assessment.read", group: "Assessment" },
  { label: "Attainment", href: "/attainment", icon: BarChart3, permission: "attainment.read", group: "Assessment" },

  // Reports & Accreditation
  { label: "Reports", href: "/reports", icon: FileText, permission: "report.export", group: "Reports" },
  { label: "Accreditation", href: "/accreditation", icon: Award, permission: "accreditation.cycle.manage", group: "Reports" },

  // System
  { label: "Notifications", href: "/notifications", icon: Bell, permission: null, group: "System" },
  { label: "Audit Log", href: "/audit", icon: ScrollText, permission: "system.audit.read", group: "System" },
]

export const NAV_GROUPS = ["Core", "Administration", "Curriculum", "OBE", "Assessment", "Reports", "System"] as const
