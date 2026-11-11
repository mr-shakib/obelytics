"use client"

import "katex/dist/katex.min.css"
import ReactMarkdown from "react-markdown"
import rehypeKatex from "rehype-katex"
import remarkGfm from "remark-gfm"
import remarkMath from "remark-math"

import { cn } from "@/lib/utils"

/** Question wording as the AI read it: Markdown tables and LaTeX math. */
export function QuestionText({ text, className }: { text: string; className?: string }) {
  return (
    <div className={cn("space-y-2 text-sm [&_.katex]:text-[1.05em]", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false }]]}
        components={{
          table: ({ children }) => (
            <div className="w-fit max-w-full overflow-x-auto rounded-md border">
              <table className="border-collapse text-sm tabular-nums">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="border-b bg-muted/50 px-3 py-1 text-left font-medium">{children}</th>,
          td: ({ children }) => <td className="border-t px-3 py-1">{children}</td>,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  )
}
