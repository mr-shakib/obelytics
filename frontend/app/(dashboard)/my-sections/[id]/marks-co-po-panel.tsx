"use client"

import { useQuery } from "@tanstack/react-query"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui/table"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

type COAttainment = {
  course_outcome_id: string
  co_code: string
  max_marks: number
}

type POAttainment = {
  program_outcome_id: string
  po_code: string
  max_marks: number
}

type StudentAttainmentRow = {
  enrollment_id: string
  student_id_number: string
  full_name: string
  co_marks: Record<string, number>
  co_pct: Record<string, number>
  po_marks: Record<string, number>
  po_pct: Record<string, number>
}

type AttainmentResponse = {
  cos: COAttainment[]
  pos: POAttainment[]
  students: StudentAttainmentRow[]
  threshold_co_score_pct: number
}

interface Props {
  sectionOfferingId: string
}

export function MarksCoPoPanel({ sectionOfferingId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.marksheets.attainment(sectionOfferingId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/marksheets/${sectionOfferingId}/attainment` as never)
      return (data as unknown) as AttainmentResponse
    },
  })

  if (isLoading) return <div className="h-64 animate-pulse bg-muted rounded-lg" />
  if (!data) return <p className="text-muted-foreground">Attainment data not available.</p>

  const naturalSort = (a: string, b: string) =>
    a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" })
  const cos = [...data.cos].sort((a, b) => naturalSort(a.co_code, b.co_code))
  const pos = [...data.pos].sort((a, b) => naturalSort(a.po_code, b.po_code))
  const threshold = Number(data.threshold_co_score_pct)

  if (data.students.length === 0) {
    return <p className="text-muted-foreground">No students enrolled in this section.</p>
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">
          Marks vs CO/PO
          <span className="ml-2 text-xs font-normal text-muted-foreground">
            Below threshold: &lt; {threshold}%
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Name</TableHead>
              {cos.map((co) => (
                <TableHead key={co.course_outcome_id} className="text-center bg-blue-200 text-blue-950 dark:bg-blue-900/70 dark:text-blue-50">
                  {co.co_code}
                  <span className="block text-[10px] font-normal text-muted-foreground">
                    /{Number(co.max_marks)}
                  </span>
                </TableHead>
              ))}
              {pos.map((po) => (
                <TableHead key={po.program_outcome_id} className="text-center bg-amber-200 text-amber-950 dark:bg-amber-900/70 dark:text-amber-50">
                  {po.po_code}
                  <span className="block text-[10px] font-normal text-muted-foreground">
                    /{Number(po.max_marks)}
                  </span>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.students.map((student) => (
              <TableRow key={student.enrollment_id}>
                <TableCell className="font-mono text-xs">{student.student_id_number}</TableCell>
                <TableCell>{student.full_name}</TableCell>
                {cos.map((co) => {
                  const pct = Number(student.co_pct[co.co_code] ?? 0)
                  const belowThreshold = pct < threshold
                  return (
                    <TableCell
                      key={co.course_outcome_id}
                      className={cn(
                        "text-center bg-blue-100/80 dark:bg-blue-950/40",
                        belowThreshold && "bg-red-100 text-red-800 font-semibold dark:bg-red-950/35 dark:text-red-200"
                      )}
                    >
                      {Number(student.co_marks[co.co_code] ?? 0)} / {Number(co.max_marks)}
                      <span className={cn(
                        "block text-[10px]",
                        belowThreshold ? "text-red-700 dark:text-red-200" : "text-muted-foreground"
                      )}>
                        {pct.toFixed(1)}%
                      </span>
                    </TableCell>
                  )
                })}
                {pos.map((po) => {
                  const pct = Number(student.po_pct[po.po_code] ?? 0)
                  const belowThreshold = pct < threshold
                  return (
                    <TableCell
                      key={po.program_outcome_id}
                      className={cn(
                        "text-center bg-amber-100/80 dark:bg-amber-950/40",
                        belowThreshold && "bg-red-100 text-red-800 font-semibold dark:bg-red-950/35 dark:text-red-200"
                      )}
                    >
                      {Number(student.po_marks[po.po_code] ?? 0)} / {Number(po.max_marks)}
                      <span className={cn(
                        "block text-[10px]",
                        belowThreshold ? "text-red-700 dark:text-red-200" : "text-muted-foreground"
                      )}>
                        {pct.toFixed(1)}%
                    </span>
                    </TableCell>
                  )
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
