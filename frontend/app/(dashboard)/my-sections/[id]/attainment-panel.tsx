"use client"

import { useQuery } from "@tanstack/react-query"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts"

import { Badge } from "@/components/ui/badge"
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
  average_attainment_pct: number
  students_above_threshold: number
  total_students: number
  is_attained: boolean
}

type POAttainment = {
  program_outcome_id: string
  po_code: string
  max_marks: number
  attainment_pct: number
  contributing_co_count: number
  students_above_threshold: number
  total_students: number
  is_attained: boolean
}

type StudentAttainmentRow = {
  enrollment_id: string
  student_id_number: string
  full_name: string
  co_results: Record<string, boolean>
  po_results: Record<string, boolean>
}

type AttainmentResponse = {
  threshold_co_score_pct: number
  cos: COAttainment[]
  pos: POAttainment[]
  students: StudentAttainmentRow[]
}

interface Props {
  sectionOfferingId: string
}

function AttainmentBar({
  data,
  threshold,
  label,
}: {
  data: { code: string; value: number; attained: boolean }[]
  threshold: number
  label: string
}) {
  if (data.length === 0) return <p className="text-sm text-muted-foreground">No data available.</p>
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="code" tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
        <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}%`, label]} />
        <ReferenceLine y={threshold} stroke="#f59e0b" strokeDasharray="4 2" label={{ value: "Threshold", fontSize: 10 }} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map((entry) => (
            <Cell key={entry.code} fill={entry.attained ? "#22c55e" : "#ef4444"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function AttainmentPanel({ sectionOfferingId }: Props) {
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
  const sortedCos = [...data.cos].sort((a, b) => naturalSort(a.co_code, b.co_code))
  const sortedPos = [...data.pos].sort((a, b) => naturalSort(a.po_code, b.po_code))

  const coData = sortedCos.map((c) => ({
    code: c.co_code,
    value: c.total_students > 0
      ? Math.round((c.students_above_threshold / c.total_students) * 1000) / 10
      : 0,
    attained: c.is_attained,
  }))
  const poData = sortedPos.map((p) => ({
    code: p.po_code,
    value: p.total_students > 0
      ? Math.round((p.students_above_threshold / p.total_students) * 1000) / 10
      : 0,
    attained: p.is_attained,
  }))

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        <Badge variant="outline">Attainment threshold: {Number(data.threshold_co_score_pct)}%</Badge>
        <Badge variant="secondary">% achieved = students at/above threshold</Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Course Outcome Attainment</CardTitle>
          </CardHeader>
          <CardContent>
            <AttainmentBar data={coData} threshold={Number(data.threshold_co_score_pct)} label="% Students Achieved" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Program Outcome Attainment</CardTitle>
          </CardHeader>
          <CardContent>
            <AttainmentBar data={poData} threshold={Number(data.threshold_co_score_pct)} label="% Students Achieved" />
          </CardContent>
        </Card>
      </div>

      {sortedCos.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">CO Attainment Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead></TableHead>
                  {sortedCos.map((co) => (
                    <TableHead key={co.course_outcome_id} className="text-center">{co.co_code}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell className="font-medium">No. of Students Who Attempted</TableCell>
                  {sortedCos.map((co) => (
                    <TableCell key={co.course_outcome_id} className="text-center">{co.total_students}</TableCell>
                  ))}
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Threshold Marks</TableCell>
                  {sortedCos.map((co) => (
                    <TableCell key={co.course_outcome_id} className="text-center">
                      {(Number(co.max_marks) * Number(data.threshold_co_score_pct) / 100).toFixed(1)}
                    </TableCell>
                  ))}
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Number of Students Achieved CO</TableCell>
                  {sortedCos.map((co) => (
                    <TableCell key={co.course_outcome_id} className="text-center">{co.students_above_threshold}</TableCell>
                  ))}
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">% of Students Achieved CO</TableCell>
                  {sortedCos.map((co) => (
                    <TableCell key={co.course_outcome_id} className="text-center">
                      {co.total_students > 0 ? Math.round((co.students_above_threshold / co.total_students) * 100) : 0}%
                    </TableCell>
                  ))}
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">CO Attained?</TableCell>
                  {sortedCos.map((co) => (
                    <TableCell key={co.course_outcome_id} className="text-center">
                      <Badge variant={co.is_attained ? "default" : "destructive"} className="text-xs">
                        {co.is_attained ? "Yes" : "No"}
                      </Badge>
                    </TableCell>
                  ))}
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {sortedPos.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">PO Attainment Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead></TableHead>
                  {sortedPos.map((po) => (
                    <TableHead key={po.program_outcome_id} className="text-center">{po.po_code}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell className="font-medium">No. of Students Who Attempted</TableCell>
                  {sortedPos.map((po) => (
                    <TableCell key={po.program_outcome_id} className="text-center">{po.total_students}</TableCell>
                  ))}
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Threshold Marks</TableCell>
                  {sortedPos.map((po) => (
                    <TableCell key={po.program_outcome_id} className="text-center">
                      {(Number(po.max_marks) * Number(data.threshold_co_score_pct) / 100).toFixed(1)}
                    </TableCell>
                  ))}
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Number of Students Achieved PO</TableCell>
                  {sortedPos.map((po) => (
                    <TableCell key={po.program_outcome_id} className="text-center">{po.students_above_threshold}</TableCell>
                  ))}
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">% of Students Achieved PO</TableCell>
                  {sortedPos.map((po) => (
                    <TableCell key={po.program_outcome_id} className="text-center">
                      {po.total_students > 0 ? Math.round((po.students_above_threshold / po.total_students) * 100) : 0}%
                    </TableCell>
                  ))}
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">PO Attained?</TableCell>
                  {sortedPos.map((po) => (
                    <TableCell key={po.program_outcome_id} className="text-center">
                      <Badge variant={po.is_attained ? "default" : "destructive"} className="text-xs">
                        {po.is_attained ? "Yes" : "No"}
                      </Badge>
                    </TableCell>
                  ))}
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {sortedCos.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">CO Detail</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>CO</TableHead>
                  <TableHead className="text-right">Max Marks</TableHead>
                  <TableHead className="text-right">Threshold Marks</TableHead>
                  <TableHead className="text-right">% Students Achieved</TableHead>
                  <TableHead className="text-right">Students &ge; Threshold</TableHead>
                  <TableHead className="text-right">Attained</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedCos.map((co) => (
                  <TableRow key={co.course_outcome_id}>
                    <TableCell className="font-medium">{co.co_code}</TableCell>
                    <TableCell className="text-right">{Number(co.max_marks)}</TableCell>
                    <TableCell className="text-right">
                      {(Number(co.max_marks) * Number(data.threshold_co_score_pct) / 100).toFixed(1)}
                    </TableCell>
                    <TableCell className="text-right">
                      {co.total_students > 0 ? Math.round((co.students_above_threshold / co.total_students) * 100) : 0}%
                    </TableCell>
                    <TableCell className="text-right">
                      {co.students_above_threshold}/{co.total_students}
                    </TableCell>
                    <TableCell className="text-right">
                      <Badge variant={co.is_attained ? "default" : "destructive"} className="text-xs">
                        {co.is_attained ? "Yes" : "No"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {sortedPos.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">PO Detail</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>PO</TableHead>
                  <TableHead className="text-right">Contributing COs</TableHead>
                  <TableHead className="text-right">Attainment</TableHead>
                  <TableHead className="text-right">Attained</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedPos.map((po) => (
                  <TableRow key={po.program_outcome_id}>
                    <TableCell className="font-medium">{po.po_code}</TableCell>
                    <TableCell className="text-right">{po.contributing_co_count}</TableCell>
                    <TableCell className="text-right">{Number(po.attainment_pct).toFixed(1)}%</TableCell>
                    <TableCell className="text-right">
                      <Badge variant={po.is_attained ? "default" : "destructive"} className="text-xs">
                        {po.is_attained ? "Yes" : "No"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {data.students.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Per-Student Attainment (Yes/No)</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Name</TableHead>
                  {sortedCos.map((co) => (
                    <TableHead key={co.course_outcome_id} className="text-center">{co.co_code}</TableHead>
                  ))}
                  {sortedPos.map((po) => (
                    <TableHead key={po.program_outcome_id} className="text-center">{po.po_code}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.students.map((student) => (
                  <TableRow key={student.enrollment_id}>
                    <TableCell className="font-mono text-xs">{student.student_id_number}</TableCell>
                    <TableCell>{student.full_name}</TableCell>
                    {sortedCos.map((co) => (
                      <TableCell key={co.course_outcome_id} className="text-center">
                        <Badge variant={student.co_results[co.co_code] ? "default" : "destructive"} className="text-xs">
                          {student.co_results[co.co_code] ? "Yes" : "No"}
                        </Badge>
                      </TableCell>
                    ))}
                    {sortedPos.map((po) => (
                      <TableCell key={po.program_outcome_id} className="text-center">
                        <Badge variant={student.po_results[po.po_code] ? "default" : "destructive"} className="text-xs">
                          {student.po_results[po.po_code] ? "Yes" : "No"}
                        </Badge>
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
