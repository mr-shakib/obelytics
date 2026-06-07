"use client"

import { useQuery } from "@tanstack/react-query"
import { BookOpen } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { apiClient } from "@/lib/api/client"
import { formatDate } from "@/lib/utils"

export function MyCurriculumClient() {
  const { data, isLoading } = useQuery({
    queryKey: ["student", "curriculum"],
    queryFn: async () => {
      const { data } = await apiClient.GET("/assessment/students/me/curriculum" as never)
      return (data as unknown) as {
        program_name: string
        curriculum_name: string
        version: string
        effective_from: string
        courses: { code: string; title: string; credits: number; term: number; type: string }[]
      }
    },
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}
      </div>
    )
  }

  if (!data) return <p className="text-muted-foreground text-sm">No curriculum data found.</p>

  // Group courses by term
  const byTerm = data.courses.reduce<Record<number, typeof data.courses>>((acc, c) => {
    ;(acc[c.term] ??= []).push(c)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{data.program_name}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {data.curriculum_name} v{data.version} · Effective from {formatDate(data.effective_from)}
        </p>
      </div>

      {Object.entries(byTerm)
        .sort(([a], [b]) => Number(a) - Number(b))
        .map(([term, courses]) => (
          <div key={term}>
            <h2 className="font-semibold text-base mb-3 flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-primary" />
              Term {term}
            </h2>
            <div className="grid gap-2 sm:grid-cols-2">
              {courses.map((c) => (
                <Card key={c.code} className="p-0">
                  <CardContent className="p-4 flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">{c.title}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{c.code} · {c.credits} credits</p>
                    </div>
                    <Badge variant="secondary" className="text-xs">{c.type}</Badge>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ))}
    </div>
  )
}
