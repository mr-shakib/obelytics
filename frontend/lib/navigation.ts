import {
  LayoutDashboard,
  Building2,
  Building,
  GraduationCap,
  Users,
  Shield,
  ShieldCheck,
  Database,
  BookOpen,
  BookCopy,
  Users2,
  Target,
  ListChecks,
  UserCog,
  ClipboardList,
  Bell,
  FileText,
  ScrollText,
  CheckSquare,
  Settings,
  SlidersHorizontal,
  Tag,
  Boxes,
  FileSpreadsheet,
  IdCard,
  FileCheck2,
  Wrench,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"

export interface NavItem {
  label: string
  href: string
  icon: LucideIcon
  permission: string | string[] | null
  group?: string
}

export const NAV_ITEMS: NavItem[] = [
  // Core
  { label: "Dashboard", href: "/overview", icon: LayoutDashboard, permission: null, group: "Core" },
  { label: "Approvals", href: "/approvals", icon: CheckSquare, permission: null, group: "Core" },

  // Organization & IAM
  { label: "Organization", href: "/organization", icon: Building2, permission: "system.organization.configure", group: "Configuration" },
  { label: "Departments", href: "/departments", icon: Building, permission: "department.update", group: "Configuration" },
  { label: "Programs", href: "/programs", icon: GraduationCap, permission: "program.update", group: "Configuration" },
  { label: "Users", href: "/users", icon: Users, permission: "user.read", group: "Configuration" },
  { label: "Program Outcome", href: "/program-outcomes", icon: Tag, permission: ["po.create", "po.update", "po.archive"], group: "Configuration" },
  { label: "Complex Attributes", href: "/complex-attributes", icon: Boxes, permission: "config.manage", group: "Configuration" },

  // Curriculum
  { label: "Curricula", href: "/curricula", icon: BookCopy, permission: "curriculum.create", group: "Curriculum" },
  { label: "Courses", href: "/courses", icon: BookOpen, permission: "curriculum.read", group: "Curriculum" },
  { label: "Academic Batches", href: "/batches", icon: Users2, permission: "batch.create", group: "Curriculum" },
  { label: "Module Leaders", href: "/module-leaders", icon: UserCog, permission: "faculty_assignment.create", group: "Curriculum" },
  { label: "Course Outcomes", href: "/course-outcomes", icon: ListChecks, permission: "co.read", group: "Curriculum" },

  // OBE

  // Assessment
  { label: "My Sections", href: "/my-sections", icon: FileSpreadsheet, permission: "marks.enter", group: "Assessment" },
  { label: "Result Submissions", href: "/result-submissions", icon: FileCheck2, permission: ["result.approve.ml", "result.approve.pc", "result.publish"], group: "Assessment" },
  { label: "Students", href: "/students", icon: IdCard, permission: "assessment.configure", group: "Assessment" },
  // Hidden for now: the real workflow never uses these admin pages directly —
  // assessments are managed through course setup, and attainment computes
  // automatically on result publication (results feed the Reports module).
  // The routes still work by URL; re-add here to restore them to the nav.
  // { label: "Assessments", href: "/assessments", icon: ClipboardList, permission: "assessment.read", group: "Assessment" },
  // { label: "Attainment", href: "/attainment", icon: BarChart3, permission: "attainment.read", group: "Assessment" },

  // Reports & Accreditation — hidden for now; routes remain available for future use.
  // { label: "Reports", href: "/reports", icon: FileText, permission: "report.generate", group: "Reports" },
  // { label: "Accreditation", href: "/accreditation", icon: Award, permission: "accreditation.read", group: "Reports" },

  // System
  { label: "Notifications", href: "/notifications", icon: Bell, permission: null, group: "System" },
  { label: "Roles", href: "/roles", icon: Shield, permission: "system.roles.create", group: "System" },
  { label: "Permissions", href: "/role-permissions", icon: ShieldCheck, permission: "system.permissions.grant", group: "System" },
  { label: "System Settings", href: "/system-settings", icon: Wrench, permission: "system.organization.configure", group: "System" },
  { label: "Reference Data", href: "/ref-data", icon: Database, permission: "config.manage", group: "System" },
  { label: "Audit Log", href: "/audit", icon: ScrollText, permission: "system.audit.read", group: "System" },
]

export const NAV_GROUPS = ["Core", "Configuration", "Curriculum", "OBE", "Assessment", "Reports", "System"] as const

export type NavGroup = typeof NAV_GROUPS[number]

export const NAV_GROUP_META: Record<NavGroup, { icon: LucideIcon; label: string; short: string }> = {
  Core:          { icon: LayoutDashboard,   label: "Core",          short: "Core"    },
  Configuration: { icon: SlidersHorizontal, label: "Configuration", short: "Config"  },
  Curriculum:    { icon: GraduationCap,     label: "Curriculum",    short: "Curric"  },
  OBE:           { icon: Target,            label: "OBE",           short: "OBE"     },
  Assessment:    { icon: ClipboardList,     label: "Assessment",    short: "Assess"  },
  Reports:       { icon: FileText,          label: "Reports",       short: "Reports" },
  System:        { icon: Settings,          label: "System",        short: "System"  },
}

export function canViewNavItem(item: NavItem, permissions: string[]) {
  if (item.permission === null) return true
  if (Array.isArray(item.permission)) return item.permission.some((p) => permissions.includes(p))
  return permissions.includes(item.permission)
}

// Section Teachers get a focused workspace: their assigned sections (cards,
// with marks entry + attainment) plus approvals/notifications — not the full
// curriculum/assessment management nav that PCs and Module Leaders see.
const SECTION_TEACHER_NAV_HREFS = ["/my-sections", "/students", "/notifications"]

export function isSectionTeacherView(permissions: string[]) {
  return (
    permissions.includes("marks.enter") &&
    !permissions.includes("curriculum.create") &&
    !permissions.includes("co.approve")
  )
}

export function getVisibleNavItems(permissions: string[]): NavItem[] {
  if (isSectionTeacherView(permissions)) {
    return NAV_ITEMS.filter((item) => SECTION_TEACHER_NAV_HREFS.includes(item.href))
  }
  return NAV_ITEMS.filter((item) => canViewNavItem(item, permissions))
}

export function isNavItemActive(item: NavItem, pathname: string) {
  return item.href === "/overview"
    ? pathname === "/overview" || pathname === "/"
    : pathname === item.href || pathname.startsWith(item.href + "/")
}

export function getActiveNavGroup(pathname: string, items: NavItem[]): NavGroup {
  const active = items.find((item) => isNavItemActive(item, pathname))
  return (active?.group as NavGroup | undefined) ?? "Core"
}
