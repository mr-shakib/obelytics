'use client'

import { useEffect } from 'react'
import Link from 'next/link'

/* ────────────────────────────────────────────────────────────────────────────
   Landing concept: "The evidence ledger"
   Light editorial paper, ink typography, hairline rules, one green accent.
   The hero shows the product itself: attainment bars, a trend sparkline,
   the approval pipeline, and the CO–PO heatmap — evidence, not decoration.
   ──────────────────────────────────────────────────────────────────────────── */

const PO_BARS = [
  { label: 'PO1', pct: 87 },
  { label: 'PO2', pct: 78 },
  { label: 'PO3', pct: 92 },
  { label: 'PO4', pct: 64 },
  { label: 'PO5', pct: 81 },
  { label: 'PO6', pct: 73 },
]

const SPARK = [58, 63, 61, 68, 72, 70, 77, 82, 80, 86, 89, 92]

const PIPELINE = [
  { stage: 'Draft', n: 12 },
  { stage: 'Submitted', n: 27 },
  { stage: 'ML approved', n: 9 },
  { stage: 'Published', n: 214 },
]

const WORKFLOW = [
  { num: '01', title: 'Configure', desc: 'Programs, curricula, courses and outcome statements — versioned from day one.' },
  { num: '02', title: 'Map', desc: 'Course outcomes link to program outcomes with weighted intensity, on the record.' },
  { num: '03', title: 'Assess', desc: 'Teachers enter marks against outcomes; nothing is copied twice.' },
  { num: '04', title: 'Approve', desc: 'Module leaders and coordinators sign off in a chain that leaves a trail.' },
  { num: '05', title: 'Report', desc: 'Attainment computes itself. Accreditation reports export in one click.' },
]

const FEATURES = [
  {
    num: '01',
    title: 'CO–PO matrix, versioned',
    desc: 'Every mapping between a course outcome and a program outcome is weighted, dated, and auditable. When the curriculum changes, history stays.',
  },
  {
    num: '02',
    title: 'Attainment that computes itself',
    desc: 'Marks flow into CO attainment; CO attainment rolls up to PO attainment. No spreadsheets, no transcription, no Friday-night reconciliation.',
  },
  {
    num: '03',
    title: 'Approval chains with teeth',
    desc: 'Draft → Submitted → ML approved → Published. Each step is a real gate held by a real role — not a checkbox everyone shares.',
  },
  {
    num: '04',
    title: 'Accreditation-ready exports',
    desc: 'Curriculum maps, attainment summaries, section end reports and gap analyses in PDF and Excel, shaped for the reviewer across the table.',
  },
  {
    num: '05',
    title: 'Roles that match your faculty',
    desc: 'Super Admin, Program Coordinator, Module Leader, Section Teacher, Student — each sees exactly their slice, scoped by program.',
  },
  {
    num: '06',
    title: 'Trends across semesters',
    desc: 'Watch attainment move across batches and years. Find the gap two semesters before the accreditation visit does.',
  },
]

/* Placeholder entries — replace with the real team (name, role, optional link) */
const TEAM = [
  { name: 'Shakib', role: 'Founder & Lead Engineer', note: 'Architecture, backend, and the attainment engine.' },
  { name: 'Team Member', role: 'Frontend Engineer', note: 'Dashboard, analytics views, and design system.' },
  { name: 'Team Member', role: 'OBE Domain Advisor', note: 'Curriculum mapping methodology and accreditation alignment.' },
  { name: 'Team Member', role: 'QA & Operations', note: 'Faculty onboarding, data imports, and release quality.' },
]

/* CO–PO heatmap sample: 0–3 mapping intensity (sequential single-hue ramp) */
const HEAT_COS = ['CO1', 'CO2', 'CO3', 'CO4', 'CO5']
const HEAT_POS = ['PO1', 'PO2', 'PO3', 'PO4', 'PO5', 'PO6', 'PO7', 'PO8']
const HEAT = [
  [3, 2, 1, 0, 0, 1, 0, 0],
  [2, 3, 2, 1, 0, 0, 0, 0],
  [0, 1, 3, 2, 1, 0, 1, 0],
  [0, 0, 1, 3, 2, 1, 0, 1],
  [1, 0, 0, 1, 3, 2, 0, 0],
]
const HEAT_FILL = ['rgba(22,27,24,0.045)', '#c9e6d6', '#7cc4a0', '#1d7254']

function Sparkline() {
  const w = 220
  const h = 56
  const pad = 4
  const min = Math.min(...SPARK)
  const max = Math.max(...SPARK)
  const pts = SPARK.map((v, i) => {
    const x = pad + (i * (w - pad * 2)) / (SPARK.length - 1)
    const y = h - pad - ((v - min) * (h - pad * 2)) / (max - min)
    return [x, y] as const
  })
  const line = pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const area = `${line} L${pts[pts.length - 1][0].toFixed(1)},${h - pad} L${pts[0][0].toFixed(1)},${h - pad} Z`
  const [lx, ly] = pts[pts.length - 1]

  return (
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="CO attainment trend across 12 terms, rising from 58 to 92 percent" className="spark">
      <path d={area} fill="rgba(29,114,84,0.10)" />
      <path d={line} fill="none" stroke="#1d7254" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={lx} cy={ly} r="4" fill="#1d7254" stroke="#fdfdfb" strokeWidth="2" />
    </svg>
  )
}

export default function LandingPage() {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.setAttribute('data-visible', 'true')
            observer.unobserve(entry.target)
          }
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -32px 0px' }
    )
    document.querySelectorAll('[data-reveal]').forEach((el) => observer.observe(el))

    const nav = document.getElementById('ledger-nav')
    const onScroll = () => {
      if (window.scrollY > 24) nav?.setAttribute('data-scrolled', 'true')
      else nav?.removeAttribute('data-scrolled')
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => {
      observer.disconnect()
      window.removeEventListener('scroll', onScroll)
    }
  }, [])

  return (
    <>
      <style>{`
        :root {
          --paper: #faf9f6;
          --paper-2: #f2f0ea;
          --card: #fdfdfb;
          --ink: #161b18;
          --ink-70: rgba(22,27,24,0.70);
          --ink-50: rgba(22,27,24,0.50);
          --ink-35: rgba(22,27,24,0.35);
          --rule: rgba(22,27,24,0.10);
          --rule-strong: rgba(22,27,24,0.18);
          --green: #1d7254;
          --green-deep: #14523d;
          --green-wash: rgba(29,114,84,0.08);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        html { scroll-behavior: smooth; }
        body {
          background: var(--paper);
          color: var(--ink);
          font-family: var(--font-poppins), system-ui, sans-serif;
          -webkit-font-smoothing: antialiased;
        }
        ::selection { background: var(--green); color: #fff; }

        .wrap { max-width: 1120px; margin: 0 auto; padding: 0 1.5rem; }

        /* Reveal */
        [data-reveal] { opacity: 0; transform: translateY(18px); transition: opacity 0.6s ease, transform 0.6s ease; }
        [data-reveal][data-visible] { opacity: 1; transform: none; }
        @media (prefers-reduced-motion: reduce) {
          [data-reveal] { opacity: 1; transform: none; transition: none; }
        }

        /* ── Nav ── */
        #ledger-nav {
          position: fixed; top: 0; left: 0; right: 0; z-index: 100;
          background: transparent;
          transition: background 0.3s ease, box-shadow 0.3s ease;
        }
        #ledger-nav[data-scrolled] {
          background: rgba(250,249,246,0.92);
          backdrop-filter: blur(12px);
          box-shadow: 0 1px 0 var(--rule);
        }
        .nav-inner {
          display: flex; align-items: center; justify-content: space-between;
          height: 68px;
        }
        .logo {
          font-size: 1.15rem; font-weight: 700; letter-spacing: -0.02em;
          color: var(--ink); text-decoration: none;
        }
        .logo b { color: var(--green); font-weight: 700; }
        .nav-links { display: flex; align-items: center; gap: 1.75rem; }
        .nav-links a:not(.btn) {
          color: var(--ink-70); text-decoration: none;
          font-size: 0.85rem; font-weight: 500;
          transition: color 0.15s;
        }
        .nav-links a:not(.btn):hover { color: var(--ink); }
        @media (max-width: 720px) { .nav-links a:not(.btn) { display: none; } }

        .btn {
          display: inline-flex; align-items: center; gap: 0.5rem;
          text-decoration: none; font-weight: 600; font-size: 0.875rem;
          border-radius: 10px; padding: 0.65rem 1.35rem;
          transition: transform 0.15s ease, box-shadow 0.2s ease, background 0.2s ease;
        }
        .btn-ink {
          background: var(--ink); color: var(--paper);
          box-shadow: 0 2px 10px rgba(22,27,24,0.18);
        }
        .btn-ink:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(22,27,24,0.22); }
        .btn-ghost {
          color: var(--ink); border: 1px solid var(--rule-strong); background: transparent;
        }
        .btn-ghost:hover { background: var(--green-wash); border-color: var(--green); }

        /* ── Hero ── */
        .hero {
          position: relative;
          padding: 10.5rem 0 5.5rem;
          overflow: hidden;
        }
        .hero-rules {
          position: absolute; inset: 0; pointer-events: none;
          background-image: linear-gradient(var(--rule) 1px, transparent 1px);
          background-size: 100% 56px;
          mask-image: linear-gradient(to bottom, transparent, black 12%, black 68%, transparent);
          opacity: 0.5;
        }
        .hero-grid {
          position: relative;
          display: grid; grid-template-columns: 1.02fr 0.98fr;
          gap: 3.5rem; align-items: center;
        }
        @media (max-width: 920px) { .hero-grid { grid-template-columns: 1fr; gap: 3rem; } }

        .eyebrow {
          display: inline-flex; align-items: center; gap: 0.6rem;
          font-size: 0.72rem; font-weight: 600; letter-spacing: 0.16em;
          text-transform: uppercase; color: var(--green);
          margin-bottom: 1.4rem;
        }
        .eyebrow::before { content: ''; width: 26px; height: 2px; background: var(--green); border-radius: 1px; }

        h1.display {
          font-size: clamp(2.3rem, 5vw, 3.6rem);
          line-height: 1.08; letter-spacing: -0.035em; font-weight: 700;
        }
        h1.display em {
          font-style: normal; color: var(--green);
          text-decoration: underline;
          text-decoration-thickness: 3px;
          text-decoration-color: rgba(29,114,84,0.35);
          text-underline-offset: 7px;
        }
        .hero-copy {
          margin-top: 1.4rem; max-width: 33rem;
          color: var(--ink-70); font-size: 1.02rem; line-height: 1.75;
        }
        .hero-ctas { display: flex; flex-wrap: wrap; gap: 0.85rem; margin-top: 2.1rem; }
        .hero-notes {
          display: flex; flex-wrap: wrap; gap: 1.5rem;
          margin-top: 2.4rem; padding-top: 1.4rem;
          border-top: 1px solid var(--rule);
          color: var(--ink-50); font-size: 0.8rem; font-weight: 500;
        }
        .hero-notes span { display: inline-flex; align-items: center; gap: 0.45rem; }
        .hero-notes span::before { content: ''; width: 5px; height: 5px; border-radius: 50%; background: var(--green); }

        /* ── Hero widgets ── */
        .board { position: relative; display: grid; gap: 1rem; }
        .widget {
          background: var(--card);
          border: 1px solid var(--rule);
          border-radius: 16px;
          padding: 1.15rem 1.25rem;
          box-shadow: 0 1px 2px rgba(22,27,24,0.04), 0 12px 32px -18px rgba(22,27,24,0.18);
        }
        .widget-title {
          font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em;
          text-transform: uppercase; color: var(--ink-50);
          margin-bottom: 0.9rem;
        }
        .board-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
        @media (max-width: 460px) { .board-row { grid-template-columns: 1fr; } }

        .bars { display: grid; gap: 0.55rem; }
        .bar-row { display: grid; grid-template-columns: 2.4rem 1fr 2.6rem; align-items: center; gap: 0.7rem; }
        .bar-label { font-size: 0.72rem; font-weight: 600; color: var(--ink-70); }
        .bar-track { height: 10px; background: rgba(22,27,24,0.05); border-radius: 5px; overflow: hidden; }
        .bar-fill {
          height: 100%; background: var(--green); border-radius: 0 4px 4px 0;
          width: 0; transition: width 1s cubic-bezier(0.22, 1, 0.36, 1);
        }
        [data-visible] .bar-fill { width: var(--w); }
        @media (prefers-reduced-motion: reduce) { .bar-fill { width: var(--w); transition: none; } }
        .bar-val { font-size: 0.72rem; font-weight: 600; color: var(--ink-50); text-align: right; font-variant-numeric: tabular-nums; }

        .stat-num {
          font-size: 2rem; font-weight: 700; letter-spacing: -0.03em; line-height: 1;
          font-variant-numeric: tabular-nums;
        }
        .stat-num small { font-size: 1.1rem; color: var(--green); font-weight: 700; }
        .stat-sub { margin-top: 0.35rem; color: var(--ink-50); font-size: 0.75rem; }
        .spark { width: 100%; height: auto; margin-top: 0.7rem; display: block; }

        .pipe { display: grid; gap: 0.5rem; }
        .pipe-row {
          display: flex; align-items: center; justify-content: space-between;
          font-size: 0.78rem; font-weight: 500; color: var(--ink-70);
          padding: 0.42rem 0.6rem; border-radius: 8px; background: rgba(22,27,24,0.028);
        }
        .pipe-row b { font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums; }
        .pipe-row[data-hot] { background: var(--green-wash); }
        .pipe-row[data-hot] b { color: var(--green-deep); }

        /* ── Section scaffolding ── */
        section.block { padding: 5.5rem 0; }
        section.block + section.block { border-top: 1px solid var(--rule); }
        .block-head { max-width: 40rem; margin-bottom: 3.2rem; }
        .block-kicker {
          font-size: 0.72rem; font-weight: 600; letter-spacing: 0.16em;
          text-transform: uppercase; color: var(--green); margin-bottom: 0.9rem;
        }
        h2.block-title {
          font-size: clamp(1.6rem, 3.2vw, 2.3rem);
          letter-spacing: -0.03em; line-height: 1.15; font-weight: 700;
        }
        .block-sub { margin-top: 0.9rem; color: var(--ink-70); line-height: 1.7; font-size: 0.95rem; }

        /* ── Workflow ledger ── */
        .steps { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0; border-top: 1px solid var(--rule-strong); }
        @media (max-width: 920px) { .steps { grid-template-columns: 1fr; border-top: none; } }
        .step { padding: 1.6rem 1.4rem 0 0; position: relative; }
        @media (max-width: 920px) {
          .step { border-top: 1px solid var(--rule-strong); padding: 1.4rem 0; }
        }
        .step::before {
          content: ''; position: absolute; top: -1px; left: 0;
          width: 34px; height: 2px; background: var(--green);
        }
        .step-num { font-size: 0.72rem; font-weight: 700; color: var(--green); letter-spacing: 0.1em; }
        .step-title { margin-top: 0.55rem; font-weight: 600; font-size: 1.02rem; letter-spacing: -0.01em; }
        .step-desc { margin-top: 0.5rem; color: var(--ink-70); font-size: 0.83rem; line-height: 1.65; }

        /* ── Feature index ── */
        .features { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; background: var(--rule); border: 1px solid var(--rule); border-radius: 18px; overflow: hidden; }
        @media (max-width: 920px) { .features { grid-template-columns: 1fr 1fr; } }
        @media (max-width: 620px) { .features { grid-template-columns: 1fr; } }
        .feature {
          background: var(--card); padding: 1.8rem 1.6rem;
          transition: background 0.2s ease;
        }
        .feature:hover { background: #f7faf8; }
        .feature-num { font-size: 0.72rem; font-weight: 700; color: var(--ink-35); letter-spacing: 0.1em; }
        .feature:hover .feature-num { color: var(--green); }
        .feature-title { margin-top: 0.7rem; font-weight: 600; font-size: 1rem; letter-spacing: -0.01em; }
        .feature-desc { margin-top: 0.55rem; color: var(--ink-70); font-size: 0.83rem; line-height: 1.7; }

        /* ── Matrix section ── */
        .matrix-grid {
          display: grid; grid-template-columns: 0.9fr 1.1fr; gap: 3.5rem; align-items: center;
        }
        @media (max-width: 920px) { .matrix-grid { grid-template-columns: 1fr; gap: 2.5rem; } }
        .heat { border-collapse: separate; border-spacing: 2px; width: 100%; }
        .heat th {
          font-size: 0.62rem; font-weight: 600; color: var(--ink-50);
          padding: 0.25rem; text-align: center; letter-spacing: 0.04em;
        }
        .heat td {
          border-radius: 5px; height: 30px; min-width: 30px;
          text-align: center; font-size: 0.62rem; font-weight: 600;
        }
        .heat td[data-v="0"] { color: transparent; }
        .heat td[data-v="1"] { color: var(--green-deep); }
        .heat td[data-v="2"] { color: #fff; }
        .heat td[data-v="3"] { color: #fff; }
        .heat-legend {
          display: flex; align-items: center; gap: 0.9rem;
          margin-top: 0.9rem; font-size: 0.7rem; color: var(--ink-50); font-weight: 500;
        }
        .heat-legend i {
          display: inline-flex; align-items: center; gap: 0.35rem; font-style: normal;
        }
        .heat-legend i::before {
          content: ''; width: 12px; height: 12px; border-radius: 3px; background: var(--c);
          border: 1px solid var(--rule);
        }

        /* ── Team ── */
        .team { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.4rem; }
        @media (max-width: 920px) { .team { grid-template-columns: 1fr 1fr; } }
        @media (max-width: 540px) { .team { grid-template-columns: 1fr; } }
        .member {
          border-top: 1px solid var(--rule-strong);
          padding-top: 1.3rem;
          position: relative;
        }
        .member::before {
          content: ''; position: absolute; top: -1px; left: 0;
          width: 34px; height: 2px; background: var(--green);
          transition: width 0.25s ease;
        }
        .member:hover::before { width: 100%; }
        .member-avatar {
          width: 52px; height: 52px; border-radius: 14px;
          display: flex; align-items: center; justify-content: center;
          background: var(--green-wash); color: var(--green-deep);
          font-weight: 700; font-size: 1.05rem; letter-spacing: -0.02em;
          border: 1px solid var(--rule);
          margin-bottom: 0.9rem;
        }
        .member-name { font-weight: 600; font-size: 0.98rem; letter-spacing: -0.01em; }
        .member-role { margin-top: 0.15rem; color: var(--green-deep); font-size: 0.76rem; font-weight: 600; }
        .member-note { margin-top: 0.5rem; color: var(--ink-70); font-size: 0.8rem; line-height: 1.65; }

        /* ── CTA band ── */
        .cta-band {
          margin: 5.5rem 0;
          background: var(--green-deep);
          border-radius: 24px;
          padding: 4rem 3rem;
          text-align: center;
          position: relative; overflow: hidden;
        }
        .cta-band::before {
          content: ''; position: absolute; inset: 0;
          background-image: linear-gradient(rgba(250,249,246,0.06) 1px, transparent 1px);
          background-size: 100% 40px;
          pointer-events: none;
        }
        .cta-band h2 {
          position: relative;
          color: #fdfdfb; font-size: clamp(1.6rem, 3.4vw, 2.4rem);
          letter-spacing: -0.03em; font-weight: 700; line-height: 1.15;
        }
        .cta-band p {
          position: relative;
          color: rgba(253,253,251,0.75); margin: 1rem auto 0; max-width: 34rem;
          font-size: 0.95rem; line-height: 1.7;
        }
        .cta-band .btn {
          position: relative; margin-top: 2rem;
          background: #fdfdfb; color: var(--green-deep);
          box-shadow: 0 4px 18px rgba(0,0,0,0.25);
        }
        .cta-band .btn:hover { transform: translateY(-1px); }

        /* ── Footer ── */
        footer {
          border-top: 1px solid var(--rule);
          padding: 2.2rem 0 2.6rem;
          display: flex; align-items: center; justify-content: space-between;
          flex-wrap: wrap; gap: 1rem;
          color: var(--ink-50); font-size: 0.8rem;
        }
        footer a { color: var(--ink-70); text-decoration: none; font-weight: 500; }
        footer a:hover { color: var(--ink); }
      `}</style>

      {/* ── Nav ── */}
      <nav id="ledger-nav">
        <div className="wrap nav-inner">
          <Link href="/" className="logo">Obelytics<b>.</b></Link>
          <div className="nav-links">
            <a href="#workflow">Workflow</a>
            <a href="#platform">Platform</a>
            <a href="#matrix">CO–PO Matrix</a>
            <a href="#team">Team</a>
            <Link href="/result">Check result</Link>
            <Link href="/login" className="btn btn-ink">Sign in</Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <header className="hero">
        <div className="hero-rules" aria-hidden="true" />
        <div className="wrap hero-grid">
          <div data-reveal>
            <p className="eyebrow">Outcome-based education, operationalized</p>
            <h1 className="display">
              Accreditation evidence, <em>computed</em> — not compiled.
            </h1>
            <p className="hero-copy">
              Obelytics runs your entire OBE workflow — outcomes, mappings, marks,
              approvals, and attainment — in one system of record. When the
              accreditation visit comes, the evidence is already there.
            </p>
            <div className="hero-ctas">
              <Link href="/login" className="btn btn-ink">Open the dashboard</Link>
              <Link href="/result" className="btn btn-ghost">Check your result</Link>
            </div>
            <div className="hero-notes">
              <span>Washington Accord aligned</span>
              <span>BAETE-ready reports</span>
              <span>Full audit trail</span>
            </div>
          </div>

          <div className="board" data-reveal aria-hidden="true">
            <div className="widget">
              <p className="widget-title">PO attainment — Spring 2026</p>
              <div className="bars">
                {PO_BARS.map((b) => (
                  <div className="bar-row" key={b.label}>
                    <span className="bar-label">{b.label}</span>
                    <span className="bar-track">
                      <span className="bar-fill" style={{ ['--w' as never]: `${b.pct}%` }} />
                    </span>
                    <span className="bar-val">{b.pct}%</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="board-row">
              <div className="widget">
                <p className="widget-title">Avg CO attainment</p>
                <p className="stat-num">92.4<small>%</small></p>
                <p className="stat-sub">across 12 terms</p>
                <Sparkline />
              </div>
              <div className="widget">
                <p className="widget-title">Result pipeline</p>
                <div className="pipe">
                  {PIPELINE.map((p) => (
                    <div className="pipe-row" key={p.stage} data-hot={p.stage === 'Submitted' ? '' : undefined}>
                      <span>{p.stage}</span>
                      <b>{p.n}</b>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* ── Workflow ── */}
      <section className="block" id="workflow">
        <div className="wrap">
          <div className="block-head" data-reveal>
            <p className="block-kicker">The workflow</p>
            <h2 className="block-title">Five steps, one unbroken chain of custody.</h2>
            <p className="block-sub">
              From the first outcome statement to the final published result, every
              artifact stays connected to the one before it.
            </p>
          </div>
          <div className="steps" data-reveal>
            {WORKFLOW.map((s) => (
              <div className="step" key={s.num}>
                <p className="step-num">{s.num}</p>
                <p className="step-title">{s.title}</p>
                <p className="step-desc">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Platform ── */}
      <section className="block" id="platform">
        <div className="wrap">
          <div className="block-head" data-reveal>
            <p className="block-kicker">The platform</p>
            <h2 className="block-title">Everything the spreadsheet was pretending to do.</h2>
          </div>
          <div className="features" data-reveal>
            {FEATURES.map((f) => (
              <div className="feature" key={f.num}>
                <p className="feature-num">{f.num}</p>
                <p className="feature-title">{f.title}</p>
                <p className="feature-desc">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Matrix ── */}
      <section className="block" id="matrix">
        <div className="wrap matrix-grid">
          <div data-reveal>
            <p className="block-kicker">The signature artifact</p>
            <h2 className="block-title">The CO–PO matrix, as a living document.</h2>
            <p className="block-sub">
              Mapping intensity is recorded on a 0–3 scale, weighted into every
              attainment calculation, and versioned with the curriculum. Change a
              mapping and the analytics follow — the old version stays on file.
            </p>
          </div>
          <div data-reveal>
            <table className="heat" role="img" aria-label="Sample CO to PO mapping matrix with intensity from 0 to 3">
              <thead>
                <tr>
                  <th aria-hidden="true" />
                  {HEAT_POS.map((po) => <th key={po}>{po}</th>)}
                </tr>
              </thead>
              <tbody>
                {HEAT.map((row, r) => (
                  <tr key={HEAT_COS[r]}>
                    <th scope="row">{HEAT_COS[r]}</th>
                    {row.map((v, c) => (
                      <td key={c} data-v={v} style={{ background: HEAT_FILL[v] }}>
                        {v || ''}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="heat-legend">
              <span>Mapping intensity</span>
              <i style={{ ['--c' as never]: HEAT_FILL[0] }}>0</i>
              <i style={{ ['--c' as never]: HEAT_FILL[1] }}>1</i>
              <i style={{ ['--c' as never]: HEAT_FILL[2] }}>2</i>
              <i style={{ ['--c' as never]: HEAT_FILL[3] }}>3</i>
            </div>
          </div>
        </div>
      </section>

      {/* ── Team ── */}
      <section className="block" id="team">
        <div className="wrap">
          <div className="block-head" data-reveal>
            <p className="block-kicker">The people</p>
            <h2 className="block-title">Built close to the faculty room.</h2>
            <p className="block-sub">
              Obelytics is built by people who have sat through the accreditation
              audits, the mapping workshops, and the result-submission deadlines.
            </p>
          </div>
          <div className="team" data-reveal>
            {TEAM.map((m, i) => (
              <div className="member" key={i}>
                <div className="member-avatar" aria-hidden="true">
                  {m.name.split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase()}
                </div>
                <p className="member-name">{m.name}</p>
                <p className="member-role">{m.role}</p>
                <p className="member-note">{m.note}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <div className="wrap">
        <div className="cta-band" data-reveal>
          <h2>The next accreditation cycle starts now.</h2>
          <p>
            Put your program&apos;s outcomes, assessments, and approvals in one place —
            and let the evidence write itself.
          </p>
          <Link href="/login" className="btn">Open the dashboard</Link>
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="wrap">
        <footer>
          <span>© {new Date().getFullYear()} Obelytics — Outcome-Based Education Analytics</span>
          <span style={{ display: 'flex', gap: '1.5rem' }}>
            <a href="#workflow">Workflow</a>
            <a href="#platform">Platform</a>
            <Link href="/result">Check result</Link>
            <Link href="/login">Sign in</Link>
          </span>
        </footer>
      </div>
    </>
  )
}
