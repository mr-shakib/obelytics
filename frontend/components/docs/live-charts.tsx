"use client"

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

type Props = {
  ai: { date: string; calls: number }[]
  events: { date: string; events: number }[]
}

function short(date: string) {
  const d = new Date(`${date}T00:00:00`)
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" })
}

function Chart({ title, data, dataKey, color }: {
  title: string
  data: Record<string, string | number>[]
  dataKey: string
  color: string
}) {
  const total = data.reduce((s, d) => s + Number(d[dataKey] ?? 0), 0)
  return (
    <figure className="rounded-xl border p-4">
      <figcaption className="mb-2 flex items-baseline justify-between text-sm">
        <span className="font-semibold">{title}</span>
        <span className="text-xs text-muted-foreground tabular-nums">{total} in 14 days</span>
      </figcaption>
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
            <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis allowDecimals={false} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
            <Tooltip cursor={{ fill: "var(--muted)" }} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
            <Bar dataKey={dataKey} fill={color} radius={[4, 4, 0, 0]} maxBarSize={22} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  )
}

export default function LiveCharts({ ai, events }: Props) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Chart title="AI model calls per day" data={ai.map((d) => ({ ...d, label: short(d.date) }))} dataKey="calls" color="#1d7254" />
      <Chart title="Audit events per day" data={events.map((d) => ({ ...d, label: short(d.date) }))} dataKey="events" color="#e8a33d" />
    </div>
  )
}
