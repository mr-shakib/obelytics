// Shared, deliberately restrained palette for result/attainment charts —
// replaces the ad-hoc per-chart rainbow arrays that used to live in each
// dashboard. Categorical hues are in a fixed order (never cycled/reassigned
// per render); the grade and sequential ramps are one hue stepped
// light -> dark, not a rainbow, since grades and single-series magnitudes
// are ordinal/quantitative, not distinct categories.

// Genuine multi-identity data only (e.g. "which course contributed this
// slice"). Fixed order; a 9th category should fold into "Other" rather than
// cycling back to slot 1.
export const CATEGORICAL_COLORS = [
  "#2a78d6", // blue
  "#1baf7a", // aqua
  "#eda100", // yellow
  "#008300", // green
  "#4a3aa7", // violet
  "#e34948", // red
  "#e87ba4", // magenta
  "#eb6834", // orange
]

// Stable color per entity id (e.g. a batch), hashed rather than assigned by
// array position, so the same entity reads as the same color everywhere it
// appears — across different cards, pages, and re-renders.
export function colorForId(id: string) {
  let hash = 0
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) | 0
  return CATEGORICAL_COLORS[Math.abs(hash) % CATEGORICAL_COLORS.length]
}

// Default hue for single-series magnitude charts (a course's average CO/PO
// bar, a radar series, a gauge) — one consistent "this is the data" color
// instead of a different hue per chart.
export const SEQUENTIAL_PRIMARY = "#2a78d6"

// Reserved status colors — attained/good vs not-attained/critical. Never
// reused as a decorative or categorical color.
export const STATUS_GOOD = "#0ca30c"
export const STATUS_CRITICAL = "#d03b3b"

// One hue, light -> dark, across the 10 letter grades (F lightest, A+
// darkest). Grades are ordinal, so this reads as "more attainment = more
// saturated" instead of 10 unrelated hues.
export const GRADE_RAMP: Record<string, string> = {
  "F": "#b7d3f6",
  "D": "#9ec5f4",
  "C": "#86b6ef",
  "C+": "#6da7ec",
  "B-": "#5598e7",
  "B": "#3987e5",
  "B+": "#2a78d6",
  "A-": "#256abf",
  "A": "#184f95",
  "A+": "#0d366b",
}

// Ordinal badge treatment for the result-publication workflow: unstarted
// (neutral) -> increasingly-submitted (one hue, deepening) -> published
// (terminal "done" green). Replaces the old gray/blue/cyan/teal/green mix
// where each stage had an unrelated hue.
export const RESULT_STATUS_BADGE: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
  SUBMITTED: "bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-300",
  ML_APPROVED: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200",
  PC_APPROVED: "bg-blue-200 text-blue-800 dark:bg-blue-800 dark:text-blue-100",
  PUBLISHED: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-100",
}
