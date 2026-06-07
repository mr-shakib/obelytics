import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const STATUS_STYLES: Record<string, string> = {
  // Generic
  ACTIVE: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
  INACTIVE: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",

  // CO lifecycle
  DRAFT: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
  SUBMITTED: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100",
  UNDER_REVIEW: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100",
  APPROVED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-100",
  PUBLISHED: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
  LOCKED: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100",

  // Result
  ML_APPROVED: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-100",
  PC_APPROVED: "bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-100",

  // Attainment
  INITIATED: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100",
  CALCULATED: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100",

  // Report
  PENDING: "bg-gray-100 text-gray-600",
  RUNNING: "bg-blue-100 text-blue-800",
  COMPLETED: "bg-green-100 text-green-800",
  FAILED: "bg-red-100 text-red-800",

  // Curriculum
  ARCHIVED: "bg-slate-100 text-slate-600",

  // Accreditation
  PLANNING: "bg-sky-100 text-sky-800",
  IN_PROGRESS: "bg-amber-100 text-amber-800",
  COMPLETE: "bg-green-100 text-green-800",
}

interface StatusBadgeProps {
  status: string
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const style = STATUS_STYLES[status] ?? "bg-gray-100 text-gray-600"
  return (
    <Badge
      variant="secondary"
      className={cn("border-0 font-medium", style, className)}
    >
      {status.replace(/_/g, " ")}
    </Badge>
  )
}
