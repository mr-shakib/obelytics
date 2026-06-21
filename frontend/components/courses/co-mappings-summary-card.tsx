"use client"

import { useQuery, useQueries } from "@tanstack/react-query"
import { ListChecks } from "lucide-react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

// ── Types ──────────────────────────────────────────────────────────────────────

type CourseOutcome = { id: string; code: string; statement: string; bloom_level_ids?: string[] }
type ProgramOutcome = { id: string; code: string }
type BloomLevel = { id: string; code: string; order_index: number }

type MappingSet = { id: string }
type CoPoEntry = { course_outcome_id: string; program_outcome_id: string }
type ComplexMapping = {
  course_outcome_id: string
  complex_problem_id?: string
  complex_activity_id?: string
  knowledge_profile_id?: string
}
type RefOption = { id: string; code: string; is_active: boolean }

const EMPTY_ENTRIES: CoPoEntry[] = []
const EMPTY_MAPPINGS: ComplexMapping[] = []
const EMPTY_OPTIONS: RefOption[] = []

function formatCodes(codes: (string | undefined)[]): string {
  const filtered = codes.filter((c): c is string => !!c)
  return filtered.length > 0 ? filtered.join(", ") : "—"
}

// ── Component ─────────────────────────────────────────────────────────────────

export function CoMappingsSummaryCard({
  cos,
  pos,
  bloomLevels,
  curriculumId,
  courseId,
}: {
  cos: CourseOutcome[]
  pos: ProgramOutcome[]
  bloomLevels: BloomLevel[]
  curriculumId: string
  courseId: string
}) {
  // ── CO-PO mapping set + entries ─────────────────────────────────────────

  const { data: poMappingSet } = useQuery({
    queryKey: queryKeys.coPoMappings.byCourse(curriculumId, courseId),
    queryFn: async () => {
      try {
        const { data } = (await apiClient.GET(
          `/mappings/co-po?curriculum_id=${curriculumId}&course_id=${courseId}` as never
        )) as { data: unknown }
        return ((data as unknown) as MappingSet) ?? null
      } catch {
        return null
      }
    },
    enabled: !!curriculumId && !!courseId,
    retry: false,
  })

  const poSetId = poMappingSet?.id ?? null

  const { data: poEntries = EMPTY_ENTRIES } = useQuery({
    queryKey: queryKeys.coPoMappings.entries(poSetId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/mappings/co-po/${poSetId}/entries` as never)
      return ((data as unknown) as CoPoEntry[]) ?? []
    },
    enabled: !!poSetId,
  })

  // ── CO-KP / CO-CP / CO-CA mappings (one query per CO per kind) ──────────

  const kpQueries = useQueries({
    queries: cos.map((co) => ({
      queryKey: queryKeys.complexMappings.byCo("kp", co.id),
      queryFn: async () => {
        const { data } = await apiClient.GET(`/mappings/co-kp?course_outcome_id=${co.id}` as never)
        return ((data as unknown) as ComplexMapping[]) ?? []
      },
    })),
  })

  const cpQueries = useQueries({
    queries: cos.map((co) => ({
      queryKey: queryKeys.complexMappings.byCo("cp", co.id),
      queryFn: async () => {
        const { data } = await apiClient.GET(`/mappings/co-cp?course_outcome_id=${co.id}` as never)
        return ((data as unknown) as ComplexMapping[]) ?? []
      },
    })),
  })

  const caQueries = useQueries({
    queries: cos.map((co) => ({
      queryKey: queryKeys.complexMappings.byCo("ca", co.id),
      queryFn: async () => {
        const { data } = await apiClient.GET(`/mappings/co-ca?course_outcome_id=${co.id}` as never)
        return ((data as unknown) as ComplexMapping[]) ?? []
      },
    })),
  })

  // ── Ref data for code lookups ───────────────────────────────────────────

  const { data: knowledgeProfiles = EMPTY_OPTIONS } = useQuery({
    queryKey: queryKeys.refData.knowledgeProfiles,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/knowledge-profiles" as never)
      return ((data as unknown) as RefOption[]) ?? []
    },
  })

  const { data: complexProblems = EMPTY_OPTIONS } = useQuery({
    queryKey: queryKeys.refData.complexProblems,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/complex-problems" as never)
      return ((data as unknown) as RefOption[]) ?? []
    },
  })

  const { data: complexActivities = EMPTY_OPTIONS } = useQuery({
    queryKey: queryKeys.refData.complexActivities,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/complex-activities" as never)
      return ((data as unknown) as RefOption[]) ?? []
    },
  })

  const kpById = new Map(knowledgeProfiles.map((o) => [o.id, o]))
  const cpById = new Map(complexProblems.map((o) => [o.id, o]))
  const caById = new Map(complexActivities.map((o) => [o.id, o]))
  const sortedBloomLevels = [...bloomLevels].sort((a, b) => a.order_index - b.order_index)

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <Card>
      <CardHeader>
        <CardTitle>Course Outcomes with Mappings</CardTitle>
        <CardDescription>
          Summary of each course outcome and its mapped Program Outcomes, Learning Domains, Knowledge
          Profile, Complex Engineering Problem, and Complex Engineering Activity attributes.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {cos.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border p-12 text-center">
            <ListChecks className="h-8 w-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              No course outcomes for this course yet. Add COs via &quot;Manage Course Outcomes&quot; above.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>CO</TableHead>
                  <TableHead className="min-w-[280px]">CO Statements</TableHead>
                  <TableHead>POs</TableHead>
                  <TableHead>Learning Domains</TableHead>
                  <TableHead>Knowledge Profile</TableHead>
                  <TableHead>Complex Engineering Problem</TableHead>
                  <TableHead>Complex Engineering Activities</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {cos.map((co, i) => {
                  const poCodes = pos
                    .filter((po) =>
                      poEntries.some(
                        (e) => e.course_outcome_id === co.id && e.program_outcome_id === po.id
                      )
                    )
                    .map((po) => po.code)

                  const learningDomainCodes = sortedBloomLevels
                    .filter((level) => (co.bloom_level_ids ?? []).includes(level.id))
                    .map((level) => level.code)

                  const kpMappings = kpQueries[i]?.data ?? EMPTY_MAPPINGS
                  const cpMappings = cpQueries[i]?.data ?? EMPTY_MAPPINGS
                  const caMappings = caQueries[i]?.data ?? EMPTY_MAPPINGS

                  return (
                    <TableRow key={co.id}>
                      <TableCell className="font-mono font-semibold align-top">{co.code}</TableCell>
                      <TableCell className="min-w-[280px] whitespace-normal align-top">
                        {co.statement}
                      </TableCell>
                      <TableCell className="align-top">{formatCodes(poCodes)}</TableCell>
                      <TableCell className="align-top">{formatCodes(learningDomainCodes)}</TableCell>
                      <TableCell className="align-top">
                        {formatCodes(kpMappings.map((m) => kpById.get(m.knowledge_profile_id ?? "")?.code))}
                      </TableCell>
                      <TableCell className="align-top">
                        {formatCodes(cpMappings.map((m) => cpById.get(m.complex_problem_id ?? "")?.code))}
                      </TableCell>
                      <TableCell className="align-top">
                        {formatCodes(caMappings.map((m) => caById.get(m.complex_activity_id ?? "")?.code))}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
