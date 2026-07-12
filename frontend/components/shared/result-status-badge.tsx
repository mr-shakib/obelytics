import { Badge } from "@/components/ui/badge"
import { RESULT_STATUS_BADGE } from "@/lib/result-colors"
import { cn } from "@/lib/utils"

// Ordinal treatment for the result-publication workflow (DRAFT -> SUBMITTED
// -> ML_APPROVED -> PC_APPROVED -> PUBLISHED): one hue deepening as a
// section moves through review, green only once it's actually published.
// Use this instead of the generic StatusBadge for result statuses
// specifically, so the whole result UI reads as one consistent progression
// rather than a different color per lifecycle this app has.
export function ResultStatusBadge({ status, className }: { status: string; className?: string }) {
  const style = RESULT_STATUS_BADGE[status] ?? "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300"
  return (
    <Badge variant="secondary" className={cn("border-0 font-medium", style, className)}>
      {status.replace(/_/g, " ")}
    </Badge>
  )
}
