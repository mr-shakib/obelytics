"use client"

import { useState } from "react"
import Link from "next/link"
import { ArrowLeft, ArrowRight, Loader2, Printer } from "lucide-react"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell, LabelList,
} from "recharts"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

interface Outcome {
  co_code?: string
  po_code?: string
  co_statement?: string
  po_statement?: string | null
  attainment_percentage: number
  threshold: number
  is_threshold_met: boolean
}

interface CourseResult {
  course_code: string
  course_title: string
  term_name: string
  total_marks_obtained: number
  total_marks: number
  percentage: number
  grade?: string | null
  co_results: Outcome[]
  po_results: Outcome[]
}

interface PublicResults {
  student_id_number: string
  full_name: string
  results: CourseResult[]
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("")
}

function Track({ code, pct, threshold, met }: {
  code: string; pct: number; threshold: number; met: boolean; index: number
}) {
  const w = Math.min(100, Math.max(0, pct))
  return (
    <div style={{ display: "grid", gridTemplateColumns: "2.8rem 1fr 2.6rem 2.9rem", alignItems: "center", gap: "0.7rem", padding: "0.32rem 0" }}>
      <span style={{ fontWeight: 700, fontSize: "0.8rem" }}>{code}</span>
      <div style={{ position: "relative", height: "9px", borderRadius: "999px", background: "#E4EAE5", overflow: "hidden" }}>
        <div style={{
          position: "absolute", left: 0, top: 0, bottom: 0,
          width: `${w}%`,
          borderRadius: "999px",
          background: met ? "linear-gradient(90deg,#1d7254,#25a876)" : "linear-gradient(90deg,#C85A2A,#B4521E)",
        }} />
        <span style={{ position: "absolute", top: 0, bottom: 0, left: `${threshold}%`, width: "2px", background: "rgba(20,33,28,0.35)" }} />
      </div>
      <span style={{ fontFamily: "ui-monospace,monospace", fontSize: "0.82rem", fontWeight: 600, textAlign: "right" }}>{pct.toFixed(0)}%</span>
      <span style={{
        fontSize: "0.65rem", fontWeight: 700, textAlign: "center",
        padding: "0.12rem 0.3rem", borderRadius: "6px",
        background: met ? "rgba(29,114,84,0.12)" : "rgba(180,82,30,0.12)",
        color: met ? "#1d7254" : "#B4521E",
      }}>{met ? "Met" : "Below"}</span>
    </div>
  )
}

// ── PO aggregation ────────────────────────────────────────────────────────────

interface POBar {
  po_code: string
  avg_pct: number
  threshold: number
  is_attained: boolean
  contributions: { course_code: string; pct: number }[]
}

function aggregatePOs(results: CourseResult[]): POBar[] {
  const map = new Map<string, { threshold: number; values: { course_code: string; pct: number }[] }>()
  for (const course of results) {
    for (const po of course.po_results ?? []) {
      if (!map.has(po.po_code!)) map.set(po.po_code!, { threshold: po.threshold, values: [] })
      map.get(po.po_code!)!.values.push({ course_code: course.course_code, pct: po.attainment_percentage })
    }
  }
  return Array.from(map.entries())
    .map(([po_code, { threshold, values }]) => {
      const avg_pct = values.reduce((s, v) => s + v.pct, 0) / values.length
      return { po_code, avg_pct, threshold, is_attained: avg_pct >= threshold, contributions: values }
    })
    .sort((a, b) => a.po_code.localeCompare(b.po_code, undefined, { numeric: true }))
}

// ── PO tooltip ────────────────────────────────────────────────────────────────

function POTooltip({ active, payload }: { active?: boolean; payload?: { payload: POBar }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={{ background: "#fff", border: "1px solid #D7E0D9", borderRadius: 10, padding: "10px 14px", fontSize: 12, minWidth: 160, boxShadow: "0 4px 16px rgba(0,0,0,0.10)" }}>
      <p style={{ fontWeight: 700, marginBottom: 4 }}>{d.po_code}</p>
      {d.contributions.map((c) => (
        <div key={c.course_code} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <span style={{ color: "#5B6862" }}>{c.course_code}</span>
          <span style={{ fontWeight: 600, color: c.pct >= d.threshold ? "#1d7254" : "#B4521E" }}>{c.pct.toFixed(1)}%</span>
        </div>
      ))}
      {d.contributions.length > 1 && (
        <div style={{ borderTop: "1px solid #E4EAE5", marginTop: 4, paddingTop: 4, display: "flex", justifyContent: "space-between", fontWeight: 700 }}>
          <span>Average</span>
          <span style={{ color: d.is_attained ? "#1d7254" : "#B4521E" }}>{d.avg_pct.toFixed(1)}%</span>
        </div>
      )}
    </div>
  )
}

// ── PO summary chart ──────────────────────────────────────────────────────────

function POSummaryChart({ results }: { results: CourseResult[] }) {
  const pos = aggregatePOs(results)
  if (pos.length === 0) return null
  const threshold = pos[0].threshold
  const attained = pos.filter((p) => p.is_attained).length
  return (
    <div style={{ background: "#fff", border: "1px solid #D7E0D9", borderRadius: 18, padding: "1.2rem 1.4rem", marginBottom: "1rem" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4, flexWrap: "wrap", gap: 8 }}>
        <div>
          <p style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#1d7254", marginBottom: 2 }}>Program Outcome Attainment</p>
          <p style={{ fontSize: "0.85rem", color: "#5B6862" }}>Average attainment across all your courses</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <span style={{ fontSize: "0.72rem", fontWeight: 700, padding: "0.25rem 0.7rem", borderRadius: 8, background: "rgba(29,114,84,0.12)", color: "#1d7254" }}>
            {attained}/{pos.length} attained
          </span>
          <span style={{ fontSize: "0.72rem", fontWeight: 600, padding: "0.25rem 0.7rem", borderRadius: 8, border: "1px solid #D7E0D9", color: "#5B6862" }}>
            Threshold {threshold}%
          </span>
        </div>
      </div>
      <div style={{ height: 240, marginTop: 8 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={pos} margin={{ top: 20, right: 8, left: -24, bottom: 4 }} barSize={26}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E4EAE5" vertical={false} />
            <XAxis dataKey="po_code" tick={{ fontSize: 11, fontWeight: 600, fill: "#14211C" }} axisLine={false} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#5B6862" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
            <Tooltip content={<POTooltip />} cursor={{ fill: "rgba(29,114,84,0.06)" }} />
            <ReferenceLine y={threshold} stroke="#B4521E" strokeDasharray="5 3"
              label={{ value: `${threshold}%`, fontSize: 9, fill: "#B4521E", position: "insideTopRight" }} />
            <Bar dataKey="avg_pct" radius={[4, 4, 0, 0]}>
              <LabelList dataKey="avg_pct" position="top"
                formatter={(v) => `${Number(v).toFixed(0)}%`}
                style={{ fontSize: 10, fontWeight: 700, fill: "#14211C" }} />
              {pos.map((p) => (
                <Cell key={p.po_code} fill={p.is_attained ? "#25a876" : "#C85A2A"} fillOpacity={0.85} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div style={{ display: "flex", gap: 16, justifyContent: "flex-end", fontSize: "0.72rem", color: "#5B6862", marginTop: 4 }}>
        <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <span style={{ width: 12, height: 12, borderRadius: 3, background: "#25a876", display: "inline-block" }} /> Attained
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <span style={{ width: 12, height: 12, borderRadius: 3, background: "#C85A2A", display: "inline-block" }} /> Not attained
        </span>
      </div>
    </div>
  )
}

export default function PublicResultPage() {
  const [uid, setUid] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<PublicResults | null>(null)

  async function lookup(e?: React.FormEvent) {
    e?.preventDefault()
    const trimmed = uid.trim()
    if (!trimmed) return
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const res = await fetch(`${BASE_URL}/api/v1/public/student-results?uid=${encodeURIComponent(trimmed)}`)
      if (res.status === 404) {
        setError("We couldn't find a student with that ID. Check the number and try again.")
        return
      }
      if (!res.ok) {
        setError("Something went wrong on our end. Please try again.")
        return
      }
      setData((await res.json()) as PublicResults)
    } catch {
      setError("Couldn't reach the server. Try again in a moment.")
    } finally {
      setLoading(false)
    }
  }

  const allCos = data?.results.flatMap((c) => c.co_results) ?? []
  const metCos = allCos.filter((o) => o.is_threshold_met).length
  const attainmentRate = allCos.length ? Math.round((metCos / allCos.length) * 100) : 0

  return (
    <div className="rc">
      <style>{`
        .rc {
          --ink: #14211C;
          --paper: #EFF3EF;
          --card: #FFFFFF;
          --line: #D7E0D9;
          --green: #1d7254;
          --green-bright: #25a876;
          --rust: #B4521E;
          --muted: #5B6862;
          --track: #E4EAE5;
          min-height: 100vh;
          background:
            radial-gradient(120% 60% at 50% -10%, rgba(37,168,118,0.06), transparent 60%),
            var(--paper);
          color: var(--ink);
          font-family: var(--font-poppins), system-ui, sans-serif;
        }
        .rc * { box-sizing: border-box; }
        .rc-mono { font-family: ui-monospace, "SF Mono", "Roboto Mono", Menlo, monospace; font-variant-numeric: tabular-nums; }

        /* Letterhead */
        .rc-head {
          background: var(--ink); color: #fff;
          border-bottom: 3px solid var(--green-bright);
        }
        .rc-head-in {
          max-width: 880px; margin: 0 auto; padding: 0.9rem 1.25rem;
          display: flex; align-items: center; justify-content: space-between;
        }
        .rc-logo { font-weight: 700; font-size: 1.15rem; letter-spacing: -0.01em; }
        .rc-logo b { color: var(--green-bright); font-weight: 700; }
        .rc-home {
          display: inline-flex; align-items: center; gap: 0.4rem;
          color: rgba(255,255,255,0.66); font-size: 0.85rem; text-decoration: none;
          transition: color 0.15s;
        }
        .rc-home:hover { color: #fff; }

        .rc-main { max-width: 880px; margin: 0 auto; padding: 2.5rem 1.25rem 4rem; }

        /* Lookup */
        .rc-eyebrow {
          font-size: 0.7rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;
          color: var(--green); margin-bottom: 0.6rem;
        }
        .rc-title { font-size: clamp(1.9rem, 5vw, 2.6rem); font-weight: 800; letter-spacing: -0.03em; line-height: 1.05; }
        .rc-lede { margin-top: 0.6rem; color: var(--muted); font-size: 1rem; max-width: 30rem; }

        .rc-form {
          margin-top: 1.75rem; display: flex; gap: 0.6rem; max-width: 30rem; flex-wrap: wrap;
        }
        .rc-input {
          flex: 1 1 14rem; min-width: 0;
          background: var(--card); border: 1.5px solid var(--line); border-radius: 12px;
          padding: 0.85rem 1rem; font-size: 1.05rem; color: var(--ink);
          letter-spacing: 0.02em; outline: none;
          transition: border-color 0.15s, box-shadow 0.15s;
          font-family: ui-monospace, "SF Mono", "Roboto Mono", Menlo, monospace;
        }
        .rc-input::placeholder { color: #9AA8A0; letter-spacing: normal; }
        .rc-input:focus { border-color: var(--green); box-shadow: 0 0 0 4px rgba(37,168,118,0.14); }
        .rc-btn {
          display: inline-flex; align-items: center; justify-content: center; gap: 0.5rem;
          background: var(--ink); color: #fff; border: none; border-radius: 12px;
          padding: 0.85rem 1.5rem; font-size: 1rem; font-weight: 600; cursor: pointer;
          transition: transform 0.12s ease, background 0.15s;
        }
        .rc-btn:hover:not(:disabled) { background: #0e1814; transform: translateY(-1px); }
        .rc-btn:disabled { opacity: 0.55; cursor: not-allowed; }
        .rc-error { margin-top: 0.9rem; color: var(--rust); font-size: 0.9rem; font-weight: 500; }

        /* Student banner */
        .rc-banner {
          margin-top: 2.5rem; background: var(--card); border: 1px solid var(--line);
          border-radius: 18px; padding: 1.25rem 1.4rem;
          display: flex; align-items: center; gap: 1.1rem; flex-wrap: wrap;
        }
        .rc-avatar {
          width: 52px; height: 52px; border-radius: 14px; flex: none;
          background: linear-gradient(140deg, var(--green), var(--green-bright));
          color: #fff; display: grid; place-items: center; font-weight: 700; font-size: 1.15rem;
        }
        .rc-name { font-size: 1.2rem; font-weight: 700; letter-spacing: -0.01em; line-height: 1.1; }
        .rc-id { color: var(--muted); font-size: 0.85rem; margin-top: 0.15rem; }
        .rc-summary { margin-left: auto; display: flex; align-items: center; gap: 1.5rem; }
        .rc-ring {
          --p: 0; width: 58px; height: 58px; border-radius: 50%; flex: none;
          background: conic-gradient(var(--green-bright) calc(var(--p) * 1%), var(--track) 0);
          display: grid; place-items: center;
        }
        .rc-ring > span {
          width: 44px; height: 44px; border-radius: 50%; background: var(--card);
          display: grid; place-items: center; font-size: 0.85rem; font-weight: 700;
        }
        .rc-stat-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); }
        .rc-stat-val { font-size: 1.35rem; font-weight: 800; line-height: 1; margin-top: 0.2rem; }
        .rc-print {
          display: inline-flex; align-items: center; gap: 0.4rem; background: none; border: none;
          color: var(--muted); font-size: 0.82rem; cursor: pointer; padding: 0.3rem 0; margin-top: 0.4rem;
        }
        .rc-print:hover { color: var(--green); }

        /* Course card */
        .rc-courses { margin-top: 1.1rem; display: flex; flex-direction: column; gap: 1rem; }
        .rc-card {
          background: var(--card); border: 1px solid var(--line); border-radius: 18px; overflow: hidden;
        }
        .rc-card-head {
          display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem;
          padding: 1.1rem 1.4rem; border-bottom: 1px solid var(--line);
        }
        .rc-course-code { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; color: var(--green); }
        .rc-course-title { font-size: 1.05rem; font-weight: 700; margin-top: 0.1rem; line-height: 1.2; }
        .rc-course-term { font-size: 0.78rem; color: var(--muted); margin-top: 0.2rem; }
        .rc-grade-wrap { text-align: right; flex: none; }
        .rc-grade {
          display: inline-block; min-width: 2.4rem; padding: 0.25rem 0.6rem; border-radius: 10px;
          background: rgba(29,114,84,0.1); color: var(--green);
          font-weight: 800; font-size: 1.05rem; letter-spacing: 0.02em;
        }
        .rc-marks { font-size: 0.82rem; color: var(--muted); margin-top: 0.35rem; }

        .rc-section { padding: 1.1rem 1.4rem; }
        .rc-section + .rc-section { border-top: 1px dashed var(--line); }
        .rc-section-label {
          font-size: 0.68rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
          color: var(--muted); margin-bottom: 0.85rem;
          display: flex; align-items: center; justify-content: space-between;
        }
        .rc-legend { font-weight: 500; letter-spacing: 0.02em; text-transform: none; color: #9AA8A0; }

        .rc-empty {
          margin-top: 1.1rem; background: var(--card); border: 1px dashed var(--line); border-radius: 18px;
          padding: 2.5rem 1.5rem; text-align: center; color: var(--muted); font-size: 0.92rem;
        }

        @media (max-width: 520px) {
          .rc-summary { margin-left: 0; width: 100%; justify-content: space-between; }
          .rc-row { grid-template-columns: 2.4rem 1fr 2.4rem 2.6rem; gap: 0.5rem; }
        }
        @media (prefers-reduced-motion: reduce) {
          .rc-fill { animation: none; }
          .rc-btn:hover { transform: none; }
        }
        @media print {
          .rc-head, .rc-eyebrow, .rc-title, .rc-lede, .rc-form, .rc-print { display: none !important; }
          .rc { background: #fff; }
          .rc-card, .rc-banner { border-color: #ccc; break-inside: avoid; }
          .rc-main { padding-top: 0.5rem; }
        }
      `}</style>

      <header className="rc-head">
        <div className="rc-head-in">
          <Link href="/" className="rc-logo">Obe<b>lytics</b></Link>
          <Link href="/" className="rc-home"><ArrowLeft className="h-4 w-4" /> Home</Link>
        </div>
      </header>

      <main className="rc-main">
        <p className="rc-eyebrow">Outcome-Based Result</p>
        <h1 className="rc-title">Check your result</h1>
        <p className="rc-lede">
          Enter your student ID to see your grades and how you attained each course and program outcome.
        </p>

        <form className="rc-form" onSubmit={lookup}>
          <input
            className="rc-input"
            value={uid}
            onChange={(e) => setUid(e.target.value)}
            placeholder="2021-1-60-001"
            aria-label="Student ID"
            autoFocus
          />
          <button className="rc-btn" type="submit" disabled={loading || !uid.trim()}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
            View result
          </button>
        </form>
        {error && <p className="rc-error">{error}</p>}

        {data && (
          <>
            <section className="rc-banner">
              <div className="rc-avatar">{initials(data.full_name)}</div>
              <div>
                <div className="rc-name">{data.full_name}</div>
                <div className="rc-id rc-mono">ID {data.student_id_number}</div>
                <button className="rc-print" onClick={() => window.print()}>
                  <Printer className="h-3.5 w-3.5" /> Save as PDF
                </button>
              </div>
              {data.results.length > 0 && (
                <div className="rc-summary">
                  <div>
                    <div className="rc-stat-label">Courses</div>
                    <div className="rc-stat-val rc-mono">{data.results.length}</div>
                  </div>
                  <div>
                    <div className="rc-stat-label">Outcomes met</div>
                    <div className="rc-stat-val rc-mono">{metCos}/{allCos.length}</div>
                  </div>
                  <div className="rc-ring" style={{ ["--p" as string]: attainmentRate }} title={`${attainmentRate}% of outcomes attained`}>
                    <span className="rc-mono">{attainmentRate}%</span>
                  </div>
                </div>
              )}
            </section>

            {data.results.length === 0 ? (
              <div className="rc-empty">
                No published results yet. They&apos;ll appear here once your department publishes them.
              </div>
            ) : (
              <>
              <POSummaryChart results={data.results} />
              <div className="rc-courses">
                {data.results.map((course) => {
                  const naturalSort = (a: string, b: string) =>
                    a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" })
                  const sortedCOs = [...course.co_results].sort((a, b) => naturalSort(a.co_code ?? "", b.co_code ?? ""))
                  const sortedPOs = [...course.po_results].sort((a, b) => naturalSort(a.po_code ?? "", b.po_code ?? ""))
                  return (
                  <article className="rc-card" key={`${course.course_code}-${course.term_name}`}>
                    <div className="rc-card-head">
                      <div>
                        <div className="rc-course-code">{course.course_code}</div>
                        <div className="rc-course-title">{course.course_title}</div>
                        <div className="rc-course-term">{course.term_name}</div>
                      </div>
                      <div className="rc-grade-wrap">
                        {course.grade && <div className="rc-grade rc-mono">{course.grade}</div>}
                        <div className="rc-marks rc-mono">
                          {course.total_marks_obtained}/{course.total_marks} · {course.percentage.toFixed(1)}%
                        </div>
                      </div>
                    </div>

                    {sortedCOs.length > 0 && (
                      <div className="rc-section">
                        <div className="rc-section-label">
                          Course Outcomes
                          <span className="rc-legend">pass line {sortedCOs[0].threshold}%</span>
                        </div>
                        {sortedCOs.map((co, i) => (
                          <Track
                            key={co.co_code}
                            code={co.co_code ?? ""}
                            pct={co.attainment_percentage}
                            threshold={co.threshold}
                            met={co.is_threshold_met}
                            index={i}
                          />
                        ))}
                      </div>
                    )}

                    {sortedPOs.length > 0 && (
                      <div className="rc-section">
                        <div className="rc-section-label">
                          Program Outcomes
                          <span className="rc-legend">pass line {sortedPOs[0].threshold}%</span>
                        </div>
                        {sortedPOs.map((po, i) => (
                          <Track
                            key={po.po_code}
                            code={po.po_code ?? ""}
                            pct={po.attainment_percentage}
                            threshold={po.threshold}
                            met={po.is_threshold_met}
                            index={i}
                          />
                        ))}
                      </div>
                    )}
                  </article>
                  )
                })}
              </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  )
}
