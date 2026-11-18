"use client"

import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

import { cn } from "@/lib/utils"

/** Markdown for docs sections. Raw HTML is not rendered (react-markdown's default). */
export function Markdown({ children, className }: { children: string; className?: string }) {
  if (!children.trim()) return null
  return (
    <div className={cn("docs-prose space-y-4 text-[0.95rem] leading-7 text-foreground/90", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h3 className="pt-2 text-xl font-semibold text-foreground">{children}</h3>,
          h2: ({ children }) => <h3 className="pt-2 text-lg font-semibold text-foreground">{children}</h3>,
          h3: ({ children }) => <h4 className="pt-2 text-base font-semibold text-foreground">{children}</h4>,
          h4: ({ children }) => <h5 className="pt-1 text-sm font-semibold text-foreground">{children}</h5>,
          p: ({ children }) => <p>{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
          ul: ({ children }) => <ul className="ml-5 list-disc space-y-1.5 marker:text-[#1d7254] dark:marker:text-[#5BD69B]">{children}</ul>,
          ol: ({ children }) => <ol className="ml-5 list-decimal space-y-1.5 marker:font-medium marker:text-muted-foreground">{children}</ol>,
          li: ({ children }) => <li className="pl-1">{children}</li>,
          a: ({ children, href }) => {
            const internal = href?.startsWith("#")
            return (
              <a
                href={href}
                {...(internal ? {} : { target: "_blank", rel: "noreferrer" })}
                className="font-medium text-[#1d7254] underline decoration-[#1d7254]/30 underline-offset-4 hover:decoration-[#1d7254] dark:text-[#5BD69B] dark:decoration-[#5BD69B]/40"
              >
                {children}
              </a>
            )
          },
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-[#1d7254]/50 pl-4 text-muted-foreground italic">{children}</blockquote>
          ),
          code: ({ children, className }) =>
            className ? (
              <code className={cn("font-mono text-[0.82rem]", className)}>{children}</code>
            ) : (
              <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[0.82rem] text-foreground">{children}</code>
            ),
          pre: ({ children }) => (
            <pre className="overflow-x-auto rounded-lg border bg-muted/50 p-4 text-[0.82rem] leading-6">{children}</pre>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto rounded-xl border print:overflow-visible">
              <table className="w-full border-collapse text-left text-sm">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-muted/60">{children}</thead>,
          th: ({ children }) => (
            <th className="border-b px-3 py-2.5 text-xs font-semibold tracking-wide text-muted-foreground uppercase">{children}</th>
          ),
          td: ({ children }) => <td className="border-b px-3 py-2.5 align-top last-of-type:border-b-0">{children}</td>,
          tr: ({ children }) => <tr className="last:[&>td]:border-b-0">{children}</tr>,
          hr: () => <hr className="my-6 border-border" />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}

/** Markdown → plain text, for search snippets. */
export function plainText(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/!\[[^\]]*]\([^)]*\)/g, " ")
    .replace(/\[([^\]]*)]\([^)]*\)/g, "$1")
    .replace(/[#>*_`|~-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
}
