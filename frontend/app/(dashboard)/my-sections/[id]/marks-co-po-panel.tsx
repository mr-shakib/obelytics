"use client"

import { useQuery } from "@tanstack/react-query"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui/table"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

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

  if (data.students.length === 0) {
    return <p className="text-muted-foreground">No students enrolled in this section.</p>
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Marks vs CO/PO</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Name</TableHead>
              {data.cos.map((co) => (
                <TableHead key={co.course_outcome_id} className="text-center">
                  {co.co_code}
                  <span className="block text-[10px] font-normal text-muted-foreground">
                    /{Number(co.max_marks)}
                  </span>
                </TableHead>
              ))}
              {data.pos.map((po) => (
                <TableHead key={po.program_outcome_id} className="text-center">
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
                {data.cos.map((co) => (
                  <TableCell key={co.course_outcome_id} className="text-center">
                    {Number(student.co_marks[co.co_code] ?? 0)} / {Number(co.max_marks)}
                    <span className="block text-[10px] text-muted-foreground">
                      {Number(student.co_pct[co.co_code] ?? 0).toFixed(1)}%
                    </span>
                  </TableCell>
                ))}
                {data.pos.map((po) => (
                  <TableCell key={po.program_outcome_id} className="text-center">
                    {Number(student.po_marks[po.po_code] ?? 0)} / {Number(po.max_marks)}
                    <span className="block text-[10px] text-muted-foreground">
                      {Number(student.po_pct[po.po_code] ?? 0).toFixed(1)}%
                    </span>
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
