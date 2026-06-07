"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { PageHeader } from "@/components/shared/page-header"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Program = { id: string; name: string; code: string }

type TrendPoint = {
  term: string
  outcomes: Record<string, number>
}

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"]

export function AttainmentTrendsClient() {
  const [programId, setProgramId] = useState<string>("")

  const { data: programs } = useQuery({
    queryKey: queryKeys.programs.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/programs" as never)
      return ((data as unknown) as { items?: Program[] })?.items ?? ((data as unknown) as Program[]) ?? []
    },
  })

  const { data: trends, isLoading } = useQuery({
    queryKey: queryKeys.attainment.trends(programId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/attainment/trends?program_id=${programId}` as never)
      return ((data as unknown) as { points?: TrendPoint[] })?.points ?? ((data as unknown) as TrendPoint[]) ?? []
    },
    enabled: !!programId,
  })

  const outcomeKeys = trends && trends.length > 0
    ? Object.keys(trends[0].outcomes)
    : []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Attainment Trends"
        description="Track outcome attainment across academic terms."
      />

      <div className="w-64">
        <Select
          value={programId}
          onValueChange={(v) => setProgramId((v as string | null) ?? "")}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select program" />
          </SelectTrigger>
          <SelectContent>
            {(programs ?? []).map((p) => (
              <SelectItem key={p.id} value={p.id}>
                {p.code} — {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {!programId && (
        <p className="text-sm text-muted-foreground">Select a program to view trends.</p>
      )}

      {programId && isLoading && (
        <div className="h-64 bg-muted animate-pulse rounded-md" />
      )}

      {programId && !isLoading && (trends ?? []).length === 0 && (
        <p className="text-sm text-muted-foreground">No trend data available yet.</p>
      )}

      {(trends ?? []).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Program Outcome Attainment Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={360}>
              <LineChart data={trends} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="term" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
                <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}%`, ""]} />
                <Legend />
                {outcomeKeys.map((key, i) => (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={`outcomes.${key}`}
                    name={key}
                    stroke={COLORS[i % COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
