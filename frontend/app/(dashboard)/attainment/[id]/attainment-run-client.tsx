"use client"

import { useQuery } from "@tanstack/react-query"
import { ArrowLeft } from "lucide-react"
import Link from "next/link"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type CoAttainment = { co_id: string; co_code: string; attainment: number; target: number }
type PoAttainment = { po_id: string; po_code: string; attainment: number; target: number }

type AttainmentRunDetail = {
  id: string
  program_name: string
  term_name?: string
  status: string
  triggered_at: string
  co_attainments: CoAttainment[]
  po_attainments: PoAttainment[]
}

interface Props {
  id: string
}

function AttainmentBar({ data, label }: { data: { code: string; attainment: number; target: number }[]; label: string }) {
  if (data.length === 0) return <p className="text-sm text-muted-foreground">No data available.</p>
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="code" tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
        <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}%`, label]} />
        <ReferenceLine y={60} stroke="#f59e0b" strokeDasharray="4 2" label={{ value: "Target", fontSize: 10 }} />
        <Bar dataKey="attainment" fill="#3b82f6" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function AttainmentRunClient({ id }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.attainment.run(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/attainment/runs/${id}` as never)
      return (data as unknown) as AttainmentRunDetail
    },
  })

  if (isLoading) return <div className="animate-pulse h-48 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Attainment run not found.</p>

  const coData = (data.co_attainments ?? []).map((c) => ({
    code: c.co_code,
    attainment: Math.round(c.attainment * 10) / 10,
    target: c.target,
  }))

  const poData = (data.po_attainments ?? []).map((p) => ({
    code: p.po_code,
    attainment: Math.round(p.attainment * 10) / 10,
    target: p.target,
  }))

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Attainment — ${data.program_name}`}
        description={data.term_name ?? "All terms"}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant={data.status === "DONE" ? "default" : "secondary"}>
              {data.status}
            </Badge>
            <Button variant="outline" size="sm" render={<Link href="/attainment" />}>
              <ArrowLeft /> Back
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Course Outcome Attainment</CardTitle>
          </CardHeader>
          <CardContent>
            <AttainmentBar data={coData} label="CO Attainment" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Program Outcome Attainment</CardTitle>
          </CardHeader>
          <CardContent>
            <AttainmentBar data={poData} label="PO Attainment" />
          </CardContent>
        </Card>
      </div>

      {coData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">CO Detail Table</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-1.5 pr-4 font-medium">CO</th>
                  <th className="py-1.5 pr-4 font-medium text-right">Attainment</th>
                  <th className="py-1.5 font-medium text-right">Target</th>
                  <th className="py-1.5 pl-4 font-medium text-right">Status</th>
                </tr>
              </thead>
              <tbody>
                {coData.map((row) => (
                  <tr key={row.code} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-medium">{row.code}</td>
                    <td className="py-2 pr-4 text-right">{row.attainment}%</td>
                    <td className="py-2 text-right text-muted-foreground">{row.target}%</td>
                    <td className="py-2 pl-4 text-right">
                      <Badge variant={row.attainment >= row.target ? "default" : "destructive"} className="text-xs">
                        {row.attainment >= row.target ? "Met" : "Below"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
