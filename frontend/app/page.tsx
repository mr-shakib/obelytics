'use client'

import { useEffect, useRef } from 'react'
import Link from 'next/link'

const FEATURES = [
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" />
      </svg>
    ),
    title: 'CO–PO Matrix Mapping',
    desc: 'Define course outcomes and map them to program outcomes with weighted intensity. Every connection is traceable, auditable, and version-controlled.',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
      </svg>
    ),
    title: 'Automated Attainment',
    desc: 'Assessment marks flow directly into CO and PO attainment calculations — no spreadsheets, no manual errors, real-time insight.',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 0 1-1.043 3.296 3.745 3.745 0 0 1-3.296 1.043A3.745 3.745 0 0 1 12 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 0 1-3.296-1.043 3.745 3.745 0 0 1-1.043-3.296A3.745 3.745 0 0 1 3 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 0 1 1.043-3.296 3.746 3.746 0 0 1 3.296-1.043A3.746 3.746 0 0 1 12 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 0 1 3.296 1.043 3.746 3.746 0 0 1 1.043 3.296A3.745 3.745 0 0 1 21 12Z" />
      </svg>
    ),
    title: 'Approval Workflows',
    desc: 'Multi-stage approval chains for mappings, assessments, and results. Draft → Submitted → Approved → Published → Locked.',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
      </svg>
    ),
    title: 'Accreditation Reports',
    desc: 'Generate OBE-ready PDF and Excel reports for accreditation bodies in seconds — curriculum maps, attainment summaries, gap analyses.',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 0 1 21.75 8.25Z" />
      </svg>
    ),
    title: 'Role-Based Access',
    desc: 'Super Admin → Program Coordinator → Module Leader → Section Teacher → Student. Granular permissions at every level.',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" />
      </svg>
    ),
    title: 'Trend Analytics',
    desc: 'Track attainment across semesters, batches, and years. Identify gaps before your next accreditation cycle with visual dashboards.',
  },
]

const STEPS = [
  { num: '01', title: 'Configure', desc: 'Set up programs, courses, and outcomes for your institution.' },
  { num: '02', title: 'Map', desc: 'Link course outcomes to program outcomes with weighted intensity.' },
  { num: '03', title: 'Assess', desc: 'Section teachers enter marks; module leaders review and approve.' },
  { num: '04', title: 'Calculate', desc: 'Attainment runs automatically across CO, course, and PO levels.' },
  { num: '05', title: 'Report', desc: 'Export accreditation-ready reports with a single click.' },
]

const MODULES = [
  { name: 'Organization Setup', icon: '🏛️' },
  { name: 'Curriculum Versioning', icon: '📚' },
  { name: 'Course Outcomes', icon: '🎯' },
  { name: 'CO–PO Matrix', icon: '⚡' },
  { name: 'Assessment Config', icon: '📝' },
  { name: 'Marks & Enrollment', icon: '✏️' },
  { name: 'Attainment Engine', icon: '🔢' },
  { name: 'Approval Chains', icon: '✅' },
  { name: 'Accreditation Cycles', icon: '🏅' },
  { name: 'Role-Based Access', icon: '🔐' },
  { name: 'Trend Analytics', icon: '📈' },
  { name: 'PDF / Excel Reports', icon: '📄' },
  { name: 'Audit Logging', icon: '🔍' },
]

const COS = ['CO1', 'CO2', 'CO3', 'CO4', 'CO5', 'CO6']
const POS = ['PO1', 'PO2', 'PO3', 'PO4', 'PO5', 'PO6', 'PO7', 'PO8', 'PO9', 'PO10', 'PO11', 'PO12']
const MAPPING = [
  [3, 2, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],
  [2, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 1, 3, 2, 1, 0, 0, 0, 1, 0, 0, 0],
  [0, 0, 1, 3, 2, 1, 0, 1, 0, 0, 0, 0],
  [0, 0, 0, 1, 3, 2, 0, 0, 0, 1, 2, 0],
  [1, 0, 0, 0, 1, 3, 2, 0, 0, 0, 1, 3],
]

function MatrixCell({ value, delay }: { value: number; delay: number }) {
  const opacity = value === 0 ? 0.06 : value === 1 ? 0.35 : value === 2 ? 0.65 : 1
  const label = value === 0 ? '' : value === 1 ? 'L' : value === 2 ? 'M' : 'H'

  return (
    <div
      className="matrix-cell"
      style={{
        animationDelay: `${delay}ms`,
        background: value === 0
          ? 'rgba(255,255,255,0.04)'
          : `rgba(37, 168, 118, ${opacity})`,
        boxShadow: value === 3 ? '0 0 12px rgba(37,168,118,0.5)' : 'none',
      }}
    >
      {label}
    </div>
  )
}

export default function LandingPage() {
  const countersStarted = useRef(false)

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.setAttribute('data-visible', 'true')
          }
        })
      },
      { threshold: 0.08, rootMargin: '0px 0px -40px 0px' }
    )
    document.querySelectorAll('[data-animate]').forEach((el) => observer.observe(el))

    const statsEl = document.getElementById('stats-section')
    const counterObs = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !countersStarted.current) {
          countersStarted.current = true
          document.querySelectorAll<HTMLElement>('[data-counter]').forEach((el) => {
            const target = parseInt(el.getAttribute('data-counter') ?? '0', 10)
            const duration = 2200
            const start = performance.now()
            const tick = (now: number) => {
              const progress = Math.min((now - start) / duration, 1)
              const eased = 1 - Math.pow(1 - progress, 3)
              el.textContent = Math.floor(eased * target).toLocaleString()
              if (progress < 1) requestAnimationFrame(tick)
            }
            requestAnimationFrame(tick)
          })
        }
      },
      { threshold: 0.5 }
    )
    if (statsEl) counterObs.observe(statsEl)

    const nav = document.getElementById('main-nav')
    const onScroll = () => {
      if (window.scrollY > 60) nav?.setAttribute('data-scrolled', 'true')
      else nav?.removeAttribute('data-scrolled')
    }
    window.addEventListener('scroll', onScroll, { passive: true })

    return () => {
      observer.disconnect()
      counterObs.disconnect()
      window.removeEventListener('scroll', onScroll)
    }
  }, [])

  return (
    <>
      <style>{`
        :root {
          --teal-darkest: #061410;
          --teal-hero: #0a1f14;
          --teal-primary: #1d7254;
          --teal-bright: #25a876;
          --teal-glow: #2dd4a0;
          --teal-mid: #175f44;
          --mint-pale: #e8f5ed;
          --mint-ultra: #f4fdf7;
          --text-dark: #0d1f17;
          --text-muted: #3d6b56;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body { background: #fff; color: var(--text-dark); font-family: var(--font-poppins), system-ui, sans-serif; }

        /* ─── NAV ─── */
        #main-nav {
          position: fixed; top: 0; left: 0; right: 0; z-index: 100;
          padding: 1.25rem 2rem;
          display: flex; align-items: center; justify-content: space-between;
          transition: background 0.4s ease, box-shadow 0.4s ease, padding 0.3s ease;
        }
        #main-nav[data-scrolled] {
          background: rgba(10, 31, 20, 0.96);
          backdrop-filter: blur(16px);
          box-shadow: 0 1px 0 rgba(37,168,118,0.15);
          padding: 0.875rem 2rem;
        }
        .nav-logo { font-size: 1.4rem; font-weight: 700; color: #fff; letter-spacing: -0.02em; }
        .nav-logo span { color: var(--teal-glow); }
        .nav-links { display: flex; gap: 2rem; align-items: center; }
        .nav-links a { color: rgba(255,255,255,0.7); text-decoration: none; font-size: 0.9rem; font-weight: 500; transition: color 0.2s; }
        .nav-links a:hover { color: #fff; }
        .nav-cta {
          background: var(--teal-primary);
          color: #fff; border: none; border-radius: 8px;
          padding: 0.5rem 1.25rem; font-size: 0.875rem; font-weight: 600;
          cursor: pointer; text-decoration: none;
          transition: background 0.2s, transform 0.15s;
        }
        .nav-cta:hover { background: var(--teal-bright); transform: translateY(-1px); }

        /* ─── HERO ─── */
        .hero {
          min-height: 100vh;
          background: var(--teal-hero);
          display: flex; align-items: center;
          position: relative; overflow: hidden;
          padding: 7rem 2rem 4rem;
        }
        .hero-bg-grid {
          position: absolute; inset: 0;
          background-image:
            linear-gradient(rgba(37,168,118,0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(37,168,118,0.05) 1px, transparent 1px);
          background-size: 48px 48px;
          animation: gridDrift 20s linear infinite;
        }
        @keyframes gridDrift {
          0% { background-position: 0 0; }
          100% { background-position: 48px 48px; }
        }
        .hero-glow {
          position: absolute; top: -20%; left: -10%;
          width: 700px; height: 700px;
          background: radial-gradient(circle, rgba(37,168,118,0.12) 0%, transparent 70%);
          animation: glowPulse 6s ease-in-out infinite alternate;
          pointer-events: none;
        }
        .hero-glow-2 {
          position: absolute; bottom: -30%; right: -5%;
          width: 600px; height: 600px;
          background: radial-gradient(circle, rgba(29,114,84,0.1) 0%, transparent 70%);
          animation: glowPulse 8s ease-in-out infinite alternate-reverse;
          pointer-events: none;
        }
        @keyframes glowPulse {
          from { opacity: 0.5; transform: scale(1); }
          to { opacity: 1; transform: scale(1.15); }
        }
        .hero-inner {
          max-width: 1280px; margin: 0 auto; width: 100%;
          display: grid; grid-template-columns: 1fr 1fr; gap: 5rem; align-items: center;
          position: relative; z-index: 2;
        }
        .hero-badge {
          display: inline-flex; align-items: center; gap: 0.5rem;
          background: rgba(37,168,118,0.12); border: 1px solid rgba(37,168,118,0.25);
          border-radius: 100px; padding: 0.375rem 1rem;
          color: var(--teal-glow); font-size: 0.8rem; font-weight: 600;
          letter-spacing: 0.05em; text-transform: uppercase;
          margin-bottom: 1.5rem;
          animation: fadeSlideDown 0.8s ease both;
        }
        .hero-badge::before {
          content: ''; display: block; width: 6px; height: 6px;
          border-radius: 50%; background: var(--teal-glow);
          animation: blink 2s ease-in-out infinite;
        }
        @keyframes blink { 0%,100% { opacity:1; } 50% { opacity:0.2; } }

        .hero-headline {
          font-size: clamp(2.6rem, 5vw, 4rem);
          font-weight: 800; line-height: 1.08; letter-spacing: -0.03em;
          color: #ffffff;
          animation: fadeSlideDown 0.9s 0.15s ease both;
        }
        .hero-headline em { font-style: normal; color: var(--teal-glow); }
        .hero-sub {
          margin-top: 1.25rem; font-size: 1.1rem; line-height: 1.65;
          color: rgba(255,255,255,0.62); font-weight: 400;
          animation: fadeSlideDown 1s 0.3s ease both;
        }
        .hero-actions {
          display: flex; gap: 1rem; align-items: center; margin-top: 2.5rem; flex-wrap: wrap;
          animation: fadeSlideDown 1s 0.45s ease both;
        }
        .btn-primary {
          background: var(--teal-bright);
          color: #fff; border: none; border-radius: 10px;
          padding: 0.875rem 2rem; font-size: 1rem; font-weight: 700;
          cursor: pointer; text-decoration: none;
          box-shadow: 0 0 32px rgba(37,168,118,0.35);
          transition: all 0.25s ease;
          position: relative; overflow: hidden;
        }
        .btn-primary::after {
          content: ''; position: absolute; inset: 0;
          background: linear-gradient(135deg, rgba(255,255,255,0.15) 0%, transparent 60%);
          opacity: 0; transition: opacity 0.25s;
        }
        .btn-primary:hover { background: var(--teal-glow); transform: translateY(-2px); box-shadow: 0 4px 40px rgba(37,168,118,0.5); }
        .btn-primary:hover::after { opacity: 1; }
        .btn-secondary {
          color: rgba(255,255,255,0.75); text-decoration: none;
          font-size: 0.95rem; font-weight: 600;
          display: flex; align-items: center; gap: 0.4rem;
          transition: color 0.2s;
        }
        .btn-secondary:hover { color: #fff; }
        .btn-secondary svg { transition: transform 0.2s; }
        .btn-secondary:hover svg { transform: translateX(4px); }

        @keyframes fadeSlideDown {
          from { opacity: 0; transform: translateY(-20px); }
          to { opacity: 1; transform: translateY(0); }
        }

        /* ─── MATRIX ─── */
        .matrix-wrapper {
          animation: fadeSlideUp 1s 0.5s ease both;
          position: relative;
        }
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(30px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .matrix-label {
          font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em;
          text-transform: uppercase; color: rgba(255,255,255,0.35);
          margin-bottom: 0.625rem;
        }
        .matrix-container {
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(37,168,118,0.2);
          border-radius: 16px;
          padding: 1.25rem;
          backdrop-filter: blur(10px);
          box-shadow: 0 0 60px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05);
        }
        .matrix-header {
          display: grid;
          grid-template-columns: 2.5rem repeat(12, 1fr);
          gap: 3px;
          margin-bottom: 3px;
        }
        .matrix-header-cell {
          text-align: center; font-size: 0.55rem; font-weight: 700;
          color: rgba(255,255,255,0.4); letter-spacing: 0.02em;
          padding: 0.25rem 0;
        }
        .matrix-row {
          display: grid;
          grid-template-columns: 2.5rem repeat(12, 1fr);
          gap: 3px; margin-bottom: 3px;
        }
        .matrix-row-label {
          display: flex; align-items: center; justify-content: flex-end;
          font-size: 0.6rem; font-weight: 700;
          color: rgba(255,255,255,0.45); padding-right: 0.375rem;
        }
        .matrix-cell {
          aspect-ratio: 1; border-radius: 4px;
          display: flex; align-items: center; justify-content: center;
          font-size: 0.5rem; font-weight: 800; color: rgba(255,255,255,0.9);
          border: 1px solid rgba(37,168,118,0.08);
          animation: cellReveal 0.5s ease both;
          transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .matrix-cell:hover { transform: scale(1.15); z-index: 2; }
        @keyframes cellReveal {
          from { opacity: 0; transform: scale(0.4); }
          to { opacity: 1; transform: scale(1); }
        }
        .matrix-legend {
          display: flex; gap: 1rem; margin-top: 0.875rem; justify-content: flex-end;
        }
        .legend-item {
          display: flex; align-items: center; gap: 0.3rem;
          font-size: 0.6rem; color: rgba(255,255,255,0.4); font-weight: 500;
        }
        .legend-dot {
          width: 10px; height: 10px; border-radius: 2px;
        }

        /* ─── STATS ─── */
        .stats-section {
          background: var(--teal-primary);
          padding: 3.5rem 2rem;
        }
        .stats-inner {
          max-width: 1000px; margin: 0 auto;
          display: grid; grid-template-columns: repeat(4, 1fr); gap: 2rem; text-align: center;
        }
        .stat-item {}
        .stat-num {
          font-size: 2.75rem; font-weight: 800; color: #fff;
          letter-spacing: -0.03em; line-height: 1;
        }
        .stat-suffix { color: var(--teal-glow); }
        .stat-label { font-size: 0.85rem; color: rgba(255,255,255,0.6); margin-top: 0.375rem; font-weight: 500; }

        /* ─── SECTION COMMONS ─── */
        .section-tag {
          display: inline-block;
          background: var(--mint-pale); color: var(--teal-primary);
          border-radius: 100px; padding: 0.3rem 0.875rem;
          font-size: 0.75rem; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase;
          margin-bottom: 1rem;
        }
        .section-heading {
          font-size: clamp(1.8rem, 3.5vw, 2.6rem);
          font-weight: 800; letter-spacing: -0.025em; line-height: 1.15;
          color: var(--text-dark);
        }
        .section-heading em { font-style: normal; color: var(--teal-primary); }
        .section-sub {
          font-size: 1rem; color: var(--text-muted); max-width: 520px; margin: 1rem auto 0; line-height: 1.65;
        }

        /* ─── FEATURES ─── */
        .features-section {
          padding: 6rem 2rem;
          background: #fff;
        }
        .features-header { text-align: center; margin-bottom: 4rem; }
        .features-grid {
          max-width: 1120px; margin: 0 auto;
          display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem;
        }
        .feature-card {
          background: var(--mint-ultra);
          border: 1px solid rgba(29,114,84,0.1);
          border-radius: 16px; padding: 2rem;
          transition: all 0.3s ease;
          cursor: default;
          opacity: 0; transform: translateY(24px);
          transition: opacity 0.5s ease, transform 0.5s ease, box-shadow 0.3s ease, border-color 0.3s ease;
        }
        .feature-card[data-visible="true"] { opacity: 1; transform: translateY(0); }
        .feature-card:hover {
          box-shadow: 0 8px 40px rgba(29,114,84,0.12);
          border-color: rgba(29,114,84,0.3);
          transform: translateY(-4px);
        }
        .feature-card:hover .feature-icon { background: var(--teal-primary); color: #fff; }
        .feature-icon {
          width: 48px; height: 48px; border-radius: 12px;
          background: rgba(29,114,84,0.1); color: var(--teal-primary);
          display: flex; align-items: center; justify-content: center;
          margin-bottom: 1.25rem;
          transition: background 0.25s, color 0.25s;
        }
        .feature-title { font-size: 1rem; font-weight: 700; color: var(--text-dark); margin-bottom: 0.5rem; }
        .feature-desc { font-size: 0.875rem; color: var(--text-muted); line-height: 1.65; }

        /* ─── HOW IT WORKS ─── */
        .workflow-section {
          padding: 6rem 2rem;
          background: var(--teal-hero);
          position: relative; overflow: hidden;
        }
        .workflow-bg {
          position: absolute; inset: 0;
          background-image:
            linear-gradient(rgba(37,168,118,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(37,168,118,0.04) 1px, transparent 1px);
          background-size: 64px 64px;
        }
        .workflow-header { text-align: center; margin-bottom: 4rem; position: relative; z-index: 1; }
        .workflow-header .section-tag { background: rgba(37,168,118,0.12); color: var(--teal-glow); }
        .workflow-header .section-heading { color: #fff; }
        .workflow-header .section-sub { color: rgba(255,255,255,0.5); }

        .workflow-steps {
          max-width: 1100px; margin: 0 auto;
          display: grid; grid-template-columns: repeat(5, 1fr);
          gap: 0; position: relative; z-index: 1;
        }
        .workflow-connector {
          position: absolute; top: 2.25rem; left: 10%; right: 10%;
          height: 1px; background: rgba(37,168,118,0.25);
          z-index: 0;
        }
        .workflow-connector-fill {
          height: 100%; width: 0%;
          background: linear-gradient(90deg, var(--teal-primary), var(--teal-glow));
          transition: width 1.5s ease;
        }
        .workflow-steps-container { position: relative; }
        .workflow-steps-container[data-visible="true"] .workflow-connector-fill { width: 100%; }
        .step {
          display: flex; flex-direction: column; align-items: center; text-align: center;
          padding: 0 1rem;
          opacity: 0; transform: translateY(20px);
          transition: opacity 0.5s ease, transform 0.5s ease;
        }
        .step[data-visible="true"] { opacity: 1; transform: translateY(0); }
        .step-num-wrap {
          width: 4.5rem; height: 4.5rem; border-radius: 50%;
          background: rgba(37,168,118,0.1);
          border: 1px solid rgba(37,168,118,0.25);
          display: flex; align-items: center; justify-content: center;
          font-size: 1.1rem; font-weight: 800; color: var(--teal-glow);
          margin-bottom: 1.25rem; position: relative; z-index: 1;
          transition: all 0.3s ease;
        }
        .step:hover .step-num-wrap {
          background: var(--teal-primary);
          box-shadow: 0 0 24px rgba(37,168,118,0.4);
          border-color: var(--teal-bright);
        }
        .step-title { font-size: 0.95rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem; }
        .step-desc { font-size: 0.78rem; color: rgba(255,255,255,0.45); line-height: 1.55; }

        /* ─── MODULES ─── */
        .modules-section {
          padding: 6rem 2rem;
          background: var(--mint-ultra);
        }
        .modules-header { text-align: center; margin-bottom: 3.5rem; }
        .modules-grid {
          max-width: 1120px; margin: 0 auto;
          display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 1rem;
        }
        .module-card {
          background: #fff;
          border: 1px solid rgba(29,114,84,0.1);
          border-radius: 12px; padding: 1.25rem 1rem;
          text-align: center;
          cursor: default;
          opacity: 0; transform: scale(0.92);
          transition: opacity 0.4s ease, transform 0.4s ease, box-shadow 0.3s ease, border-color 0.3s ease;
        }
        .module-card[data-visible="true"] { opacity: 1; transform: scale(1); }
        .module-card:hover {
          border-color: var(--teal-primary);
          box-shadow: 0 4px 24px rgba(29,114,84,0.12);
          transform: translateY(-3px) scale(1);
        }
        .module-emoji { font-size: 1.5rem; margin-bottom: 0.5rem; display: block; }
        .module-name { font-size: 0.775rem; font-weight: 600; color: var(--text-dark); line-height: 1.4; }

        /* ─── CTA ─── */
        .cta-section {
          padding: 7rem 2rem;
          background: linear-gradient(135deg, var(--teal-hero) 0%, var(--teal-mid) 50%, #0d2e1a 100%);
          text-align: center; position: relative; overflow: hidden;
        }
        .cta-glow {
          position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
          width: 600px; height: 300px;
          background: radial-gradient(ellipse, rgba(37,168,118,0.15) 0%, transparent 70%);
          pointer-events: none;
        }
        .cta-heading {
          font-size: clamp(2rem, 4vw, 3rem);
          font-weight: 800; color: #fff; letter-spacing: -0.025em;
          position: relative; z-index: 1; margin-bottom: 1rem;
        }
        .cta-heading em { font-style: normal; color: var(--teal-glow); }
        .cta-sub { font-size: 1.05rem; color: rgba(255,255,255,0.55); position: relative; z-index: 1; margin-bottom: 2.5rem; }
        .cta-actions { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; position: relative; z-index: 1; }
        .btn-outline {
          border: 1px solid rgba(255,255,255,0.25); border-radius: 10px;
          padding: 0.875rem 2rem; font-size: 1rem; font-weight: 600;
          color: rgba(255,255,255,0.8); text-decoration: none;
          transition: all 0.25s ease;
        }
        .btn-outline:hover { border-color: rgba(255,255,255,0.5); color: #fff; background: rgba(255,255,255,0.05); }

        /* ─── FOOTER ─── */
        .footer {
          background: var(--teal-darkest);
          padding: 3rem 2rem;
          display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1.5rem;
          border-top: 1px solid rgba(37,168,118,0.1);
        }
        .footer-brand { font-size: 1.1rem; font-weight: 700; color: #fff; }
        .footer-brand span { color: var(--teal-glow); }
        .footer-copy { font-size: 0.8rem; color: rgba(255,255,255,0.3); }
        .footer-links { display: flex; gap: 1.5rem; }
        .footer-links a { font-size: 0.8rem; color: rgba(255,255,255,0.4); text-decoration: none; transition: color 0.2s; }
        .footer-links a:hover { color: rgba(255,255,255,0.7); }

        /* ─── SCROLL REVEAL DELAYS ─── */
        .feature-card:nth-child(1) { transition-delay: 0.05s; }
        .feature-card:nth-child(2) { transition-delay: 0.12s; }
        .feature-card:nth-child(3) { transition-delay: 0.19s; }
        .feature-card:nth-child(4) { transition-delay: 0.26s; }
        .feature-card:nth-child(5) { transition-delay: 0.33s; }
        .feature-card:nth-child(6) { transition-delay: 0.40s; }

        .module-card:nth-child(1)  { transition-delay: 0.02s; }
        .module-card:nth-child(2)  { transition-delay: 0.05s; }
        .module-card:nth-child(3)  { transition-delay: 0.08s; }
        .module-card:nth-child(4)  { transition-delay: 0.11s; }
        .module-card:nth-child(5)  { transition-delay: 0.14s; }
        .module-card:nth-child(6)  { transition-delay: 0.17s; }
        .module-card:nth-child(7)  { transition-delay: 0.20s; }
        .module-card:nth-child(8)  { transition-delay: 0.23s; }
        .module-card:nth-child(9)  { transition-delay: 0.26s; }
        .module-card:nth-child(10) { transition-delay: 0.29s; }
        .module-card:nth-child(11) { transition-delay: 0.32s; }
        .module-card:nth-child(12) { transition-delay: 0.35s; }
        .module-card:nth-child(13) { transition-delay: 0.38s; }

        /* ─── RESPONSIVE ─── */
        @media (max-width: 1024px) {
          .hero-inner { grid-template-columns: 1fr; gap: 3rem; }
          .matrix-wrapper { max-width: 480px; margin: 0 auto; }
          .workflow-steps { grid-template-columns: 1fr 1fr; gap: 2rem; }
          .workflow-connector { display: none; }
          .features-grid { grid-template-columns: repeat(2, 1fr); }
          .stats-inner { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 640px) {
          .nav-links { display: none; }
          .features-grid { grid-template-columns: 1fr; }
          .workflow-steps { grid-template-columns: 1fr; }
          .stats-inner { grid-template-columns: repeat(2, 1fr); }
        }
        @media (prefers-reduced-motion: reduce) {
          *, .matrix-cell, .feature-card, .step, .module-card { animation: none !important; transition: none !important; }
          [data-animate], .feature-card, .module-card { opacity: 1 !important; transform: none !important; }
        }
      `}</style>

      {/* ─── NAV ─── */}
      <nav id="main-nav">
        <div className="nav-logo">Obe<span>lytics</span></div>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#workflow">How It Works</a>
          <a href="#modules">Modules</a>
          <Link href="/login" className="nav-cta">Sign In</Link>
        </div>
      </nav>

      {/* ─── HERO ─── */}
      <section className="hero">
        <div className="hero-bg-grid" />
        <div className="hero-glow" />
        <div className="hero-glow-2" />
        <div className="hero-inner">
          {/* Left: Copy */}
          <div>
            <div className="hero-badge">OBE Accreditation Platform</div>
            <h1 className="hero-headline">
              Turn outcomes into<br />
              <em>institutional excellence.</em>
            </h1>
            <p className="hero-sub">
              Obelytics automates the full OBE lifecycle — from CO–PO mapping and assessment
              to attainment calculation and accreditation reporting — so your faculty focuses
              on teaching, not spreadsheets.
            </p>
            <div className="hero-actions">
              <Link href="/login" className="btn-primary">Get Started Free</Link>
              <a href="#workflow" className="btn-secondary">
                See how it works
                <svg viewBox="0 0 16 16" fill="none" width="14" height="14" stroke="currentColor" strokeWidth="2">
                  <path d="M3 8h10M9 4l4 4-4 4" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </a>
            </div>
          </div>

          {/* Right: CO-PO Matrix */}
          <div className="matrix-wrapper">
            <p className="matrix-label">Live CO–PO Mapping Matrix</p>
            <div className="matrix-container">
              <div className="matrix-header">
                <div />
                {POS.map((po) => (
                  <div key={po} className="matrix-header-cell">{po}</div>
                ))}
              </div>
              {MAPPING.map((row, ri) => (
                <div key={ri} className="matrix-row">
                  <div className="matrix-row-label">{COS[ri]}</div>
                  {row.map((val, ci) => (
                    <MatrixCell key={ci} value={val} delay={(ri * 12 + ci) * 40 + 600} />
                  ))}
                </div>
              ))}
              <div className="matrix-legend">
                {[
                  { label: 'No link', color: 'rgba(255,255,255,0.06)' },
                  { label: 'Low', color: 'rgba(37,168,118,0.35)' },
                  { label: 'Medium', color: 'rgba(37,168,118,0.65)' },
                  { label: 'High', color: 'rgba(37,168,118,1)' },
                ].map(({ label, color }) => (
                  <div key={label} className="legend-item">
                    <div className="legend-dot" style={{ background: color, border: '1px solid rgba(37,168,118,0.2)' }} />
                    {label}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── STATS ─── */}
      <section className="stats-section" id="stats-section">
        <div className="stats-inner">
          {[
            { num: 13, suffix: '+', label: 'Integrated Modules' },
            { num: 51, suffix: '', label: 'Database Tables' },
            { num: 5, suffix: '', label: 'Role Levels' },
            { num: 12, suffix: '', label: 'Program Outcomes Supported' },
          ].map(({ num, suffix, label }) => (
            <div key={label} className="stat-item">
              <div className="stat-num">
                <span data-counter={num}>0</span>
                <span className="stat-suffix">{suffix}</span>
              </div>
              <div className="stat-label">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── FEATURES ─── */}
      <section className="features-section" id="features">
        <div className="features-header">
          <div className="section-tag">Features</div>
          <h2 className="section-heading">Everything accreditation requires,<br /><em>nothing it doesn&apos;t.</em></h2>
          <p className="section-sub">
            Built specifically for outcome-based education. Every feature maps to a real
            accreditation need — no generic EdTech bloat.
          </p>
        </div>
        <div className="features-grid">
          {FEATURES.map((f) => (
            <div key={f.title} className="feature-card" data-animate>
              <div className="feature-icon">{f.icon}</div>
              <div className="feature-title">{f.title}</div>
              <div className="feature-desc">{f.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── HOW IT WORKS ─── */}
      <section className="workflow-section" id="workflow">
        <div className="workflow-bg" />
        <div className="workflow-header" data-animate>
          <div className="section-tag">Process</div>
          <h2 className="section-heading" style={{ color: '#fff' }}>Five steps from setup<br /><em style={{ color: 'var(--teal-glow)' }}>to accreditation.</em></h2>
          <p className="section-sub" style={{ color: 'rgba(255,255,255,0.45)', margin: '1rem auto 0' }}>
            A clear path from initial configuration to board-ready reports.
          </p>
        </div>
        <div className="workflow-steps-container" data-animate>
          <div className="workflow-connector">
            <div className="workflow-connector-fill" />
          </div>
          <div className="workflow-steps">
            {STEPS.map((s, i) => (
              <div key={s.num} className="step" data-animate style={{ transitionDelay: `${i * 0.12}s` }}>
                <div className="step-num-wrap">{s.num}</div>
                <div className="step-title">{s.title}</div>
                <div className="step-desc">{s.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── MODULES ─── */}
      <section className="modules-section" id="modules">
        <div className="modules-header">
          <div className="section-tag">Platform</div>
          <h2 className="section-heading">13 modules. <em>One platform.</em></h2>
          <p className="section-sub">
            Every component of the OBE lifecycle in a unified, role-aware workspace.
          </p>
        </div>
        <div className="modules-grid">
          {MODULES.map((m) => (
            <div key={m.name} className="module-card" data-animate>
              <span className="module-emoji">{m.icon}</span>
              <div className="module-name">{m.name}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="cta-section">
        <div className="cta-glow" />
        <h2 className="cta-heading" data-animate>
          Ready to modernize<br /><em>your OBE process?</em>
        </h2>
        <p className="cta-sub" data-animate>
          Join universities that have moved from spreadsheet chaos to structured accreditation confidence.
        </p>
        <div className="cta-actions" data-animate>
          <Link href="/login" className="btn-primary">Start for Free</Link>
          <a href="mailto:asteriskshq@gmail.com" className="btn-outline">Request a Demo</a>
        </div>
      </section>

      {/* ─── FOOTER ─── */}
      <footer className="footer">
        <div className="footer-brand">Obe<span>lytics</span></div>
        <div className="footer-copy">© {new Date().getFullYear()} Obelytics. OBE Accreditation Platform.</div>
        <div className="footer-links">
          <Link href="/login">Sign In</Link>
          <a href="mailto:asteriskshq@gmail.com">Contact</a>
        </div>
      </footer>
    </>
  )
}
