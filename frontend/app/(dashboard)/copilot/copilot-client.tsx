"use client"

import { FormEvent, useEffect, useRef, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Bot, Loader2, Menu, MessageSquarePlus, Send, Trash2, User, X } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { apiFetch, PUBLIC_API_URL } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

type Conversation = {
  id: string
  title: string
  status: string
  created_at: string
  updated_at: string
  last_message_at: string | null
}

type Message = {
  id: string
  conversation_id: string
  role: "user" | "assistant"
  content: string
  status: "STREAMING" | "COMPLETE" | "FAILED"
  created_at: string
}

const API = `${PUBLIC_API_URL}/api/v1/copilot`

function AssistantMarkdown({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: ({ children, ...props }) => (
          <a {...props} target="_blank" rel="noreferrer" className="font-medium text-primary underline underline-offset-4">
            {children}
          </a>
        ),
        table: ({ children }) => (
          <div className="my-4 overflow-x-auto rounded-lg border">
            <table className="w-full border-collapse text-left text-sm">{children}</table>
          </div>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

async function readJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(`${API}${path}`, init)
  return response.json() as Promise<T>
}

export function CopilotClient() {
  const queryClient = useQueryClient()
  const [activeId, setActiveId] = useState<string | null>(null)
  const [input, setInput] = useState("")
  const [streamingMessage, setStreamingMessage] = useState<Message | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const conversationsQuery = useQuery({
    queryKey: queryKeys.copilot.conversations,
    queryFn: () => readJson<Conversation[]>("/conversations"),
  })
  const selectedConversationId = activeId ?? conversationsQuery.data?.[0]?.id ?? null

  const messagesQuery = useQuery({
    queryKey: queryKeys.copilot.messages(selectedConversationId ?? ""),
    queryFn: () => readJson<Message[]>(`/conversations/${selectedConversationId}/messages`),
    enabled: !!selectedConversationId,
  })

  const createConversation = useMutation({
    mutationFn: () =>
      readJson<Conversation>("/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New conversation", context: {} }),
      }),
    onSuccess: (conversation) => {
      queryClient.setQueryData<Conversation[]>(queryKeys.copilot.conversations, (current = []) => [
        conversation,
        ...current,
      ])
      setActiveId(conversation.id)
      setSidebarOpen(false)
    },
  })

  const deleteConversation = useMutation({
    mutationFn: async (id: string) => {
      await apiFetch(`${API}/conversations/${id}`, { method: "DELETE" })
      return id
    },
    onSuccess: (id) => {
      queryClient.setQueryData<Conversation[]>(queryKeys.copilot.conversations, (current = []) =>
        current.filter((conversation) => conversation.id !== id)
      )
      if (selectedConversationId === id) setActiveId(null)
    },
  })

  useEffect(() => {
    const viewport = bottomRef.current?.closest<HTMLElement>(
      '[data-slot="scroll-area-viewport"]'
    )
    viewport?.scrollTo({ top: viewport.scrollHeight, behavior: "smooth" })
  }, [messagesQuery.data, streamingMessage?.content])

  async function sendMessage(event: FormEvent) {
    event.preventDefault()
    const content = input.trim()
    if (!content || streamingMessage || messagesQuery.isLoading) return

    let conversationId = selectedConversationId
    if (!conversationId) {
      const conversation = await createConversation.mutateAsync()
      conversationId = conversation.id
    }

    // Keep an in-flight history request from replacing the optimistic pair and
    // making the user's message jump below the assistant response.
    await queryClient.cancelQueries({
      queryKey: queryKeys.copilot.messages(conversationId),
    })

    const optimisticUser: Message = {
      id: `user-${Date.now()}`,
      conversation_id: conversationId,
      role: "user",
      content,
      status: "COMPLETE",
      created_at: new Date().toISOString(),
    }
    queryClient.setQueryData<Message[]>(queryKeys.copilot.messages(conversationId), (current = []) => [
      ...current,
      optimisticUser,
    ])
    setInput("")
    setStreamingMessage({
      id: `assistant-${Date.now()}`,
      conversation_id: conversationId,
      role: "assistant",
      content: "",
      status: "STREAMING",
      created_at: new Date().toISOString(),
    })

    try {
      const response = await apiFetch(`${API}/conversations/${conversationId}/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ content }),
        timeoutMs: 120_000,
      } as RequestInit & { timeoutMs: number })
      if (!response.body) throw new Error("Streaming is not supported")

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      let assistantContent = ""
      let assistantId = `assistant-${Date.now()}`

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const frames = buffer.split("\n\n")
        buffer = frames.pop() ?? ""
        for (const frame of frames) {
          const eventName = frame.match(/^event: (.+)$/m)?.[1]
          const dataLine = frame.match(/^data: (.+)$/m)?.[1]
          if (!dataLine) continue
          const data = JSON.parse(dataLine) as { id?: string; content?: string; message?: string }
          if (eventName === "message" && data.id) assistantId = data.id
          if (eventName === "delta" && data.content) {
            assistantContent += data.content
            setStreamingMessage((current) =>
              current ? { ...current, id: assistantId, content: assistantContent } : current
            )
          }
          if (eventName === "error") throw new Error(data.message ?? "The copilot failed")
        }
      }

      queryClient.setQueryData<Message[]>(queryKeys.copilot.messages(conversationId), (current = []) => [
        ...current.filter((message) => message.id !== optimisticUser.id),
        optimisticUser,
        {
          id: assistantId,
          conversation_id: conversationId,
          role: "assistant",
          content: assistantContent,
          status: "COMPLETE",
          created_at: new Date().toISOString(),
        },
      ])
      queryClient.invalidateQueries({ queryKey: queryKeys.copilot.conversations })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "The copilot could not respond")
      queryClient.invalidateQueries({ queryKey: queryKeys.copilot.messages(conversationId) })
    } finally {
      setStreamingMessage(null)
    }
  }

  const storedMessages = messagesQuery.data ?? []
  const messages = streamingMessage ? [...storedMessages, streamingMessage] : storedMessages

  return (
    <div className="relative flex h-[calc(100dvh-8.5rem)] min-h-0 overflow-hidden rounded-2xl border bg-background shadow-sm">
      {sidebarOpen && (
        <button
          className="absolute inset-0 z-20 bg-black/30 md:hidden"
          aria-label="Close conversation sidebar"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <aside
        className={cn(
          "absolute inset-y-0 left-0 z-30 flex min-h-0 w-72 flex-col border-r bg-muted/30 transition-transform md:relative md:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center gap-2 border-b p-3">
          <Button className="flex-1 justify-start" onClick={() => createConversation.mutate()} disabled={createConversation.isPending}>
            <MessageSquarePlus /> New conversation
          </Button>
          <Button className="md:hidden" variant="ghost" size="icon" onClick={() => setSidebarOpen(false)}><X /></Button>
        </div>
        <ScrollArea className="min-h-0 flex-1 p-2">
          <div className="space-y-1">
            {conversationsQuery.isLoading && <p className="p-3 text-sm text-muted-foreground">Loading conversations…</p>}
            {conversationsQuery.data?.map((conversation) => (
              <div
                key={conversation.id}
                className={cn(
                  "group flex items-center rounded-lg text-sm",
                  selectedConversationId === conversation.id ? "bg-background shadow-sm" : "hover:bg-background/70"
                )}
              >
                <button
                  className="min-w-0 flex-1 truncate px-3 py-2.5 text-left"
                  onClick={() => { setActiveId(conversation.id); setSidebarOpen(false) }}
                >
                  {conversation.title}
                </button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="mr-1 opacity-0 group-hover:opacity-100"
                  aria-label="Delete conversation"
                  onClick={() => deleteConversation.mutate(conversation.id)}
                >
                  <Trash2 />
                </Button>
              </div>
            ))}
          </div>
        </ScrollArea>
        <div className="border-t p-3 text-xs text-muted-foreground">DeepSeek-powered · Suggestions require review</div>
      </aside>

      <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center gap-3 border-b px-4">
          <Button className="md:hidden" variant="ghost" size="icon" onClick={() => setSidebarOpen(true)}><Menu /></Button>
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary"><Bot className="size-4" /></div>
          <div>
            <h1 className="text-sm font-semibold">OBE Copilot</h1>
            <p className="text-xs text-muted-foreground">Role-aware assistance for your workspace</p>
          </div>
        </header>

        <ScrollArea className="min-h-0 flex-1">
          <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
            {!selectedConversationId && !messages.length && (
              <div className="flex min-h-80 flex-col items-center justify-center text-center">
                <div className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary"><Bot /></div>
                <h2 className="text-xl font-semibold">How can I help with your OBE work?</h2>
                <p className="mt-2 max-w-md text-sm text-muted-foreground">Ask about Course Outcomes, mappings, delivery plans, attainment, or pending reviews.</p>
              </div>
            )}
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn("flex gap-3", message.role === "user" && "flex-row-reverse")}
              >
                <div className={cn("mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg", message.role === "assistant" ? "bg-primary/10 text-primary" : "bg-muted")}>
                  {message.role === "assistant" ? <Bot className="size-4" /> : <User className="size-4" />}
                </div>
                <div
                  className={cn(
                    "min-w-0",
                    message.role === "assistant" ? "flex-1" : "max-w-[80%]"
                  )}
                >
                  <p className={cn("mb-1 text-xs font-medium", message.role === "user" && "text-right")}>
                    {message.role === "assistant" ? "OBE Copilot" : "You"}
                  </p>
                  <div
                    className={cn(
                      "break-words text-sm leading-6",
                      message.role === "assistant" && [
                        "[&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
                        "[&_p]:my-2.5 [&_p]:leading-6",
                        "[&_h1]:mb-3 [&_h1]:mt-6 [&_h1]:text-xl [&_h1]:font-semibold",
                        "[&_h2]:mb-2 [&_h2]:mt-5 [&_h2]:text-lg [&_h2]:font-semibold",
                        "[&_h3]:mb-2 [&_h3]:mt-4 [&_h3]:font-semibold",
                        "[&_ul]:my-3 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-6",
                        "[&_ol]:my-3 [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-6",
                        "[&_li]:pl-1 [&_li>p]:my-0",
                        "[&_strong]:font-semibold [&_strong]:text-foreground",
                        "[&_blockquote]:my-4 [&_blockquote]:border-l-2 [&_blockquote]:border-primary/40 [&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:text-muted-foreground",
                        "[&_hr]:my-5 [&_hr]:border-border",
                        "[&_code]:rounded-md [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[0.85em]",
                        "[&_pre]:my-4 [&_pre]:overflow-x-auto [&_pre]:rounded-xl [&_pre]:bg-zinc-950 [&_pre]:p-4 [&_pre]:text-zinc-100",
                        "[&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_pre_code]:text-[13px]",
                        "[&_th]:border-b [&_th]:bg-muted/60 [&_th]:px-3 [&_th]:py-2 [&_th]:font-semibold",
                        "[&_td]:border-b [&_td]:px-3 [&_td]:py-2 [&_tr:last-child_td]:border-b-0",
                      ],
                      message.role === "user" && "rounded-2xl rounded-tr-sm bg-muted px-4 py-2.5"
                    )}
                  >
                    {message.content ? (
                      message.role === "assistant" ? (
                        <AssistantMarkdown content={message.content} />
                      ) : (
                        <span className="whitespace-pre-wrap">{message.content}</span>
                      )
                    ) : (
                      message.status === "STREAMING" && <Loader2 className="size-4 animate-spin text-muted-foreground" />
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>

        <div className="border-t bg-background p-4">
          <form onSubmit={sendMessage} className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border bg-muted/20 p-2 shadow-sm focus-within:border-primary/50">
            <Textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault()
                  event.currentTarget.form?.requestSubmit()
                }
              }}
              placeholder="Message OBE Copilot"
              className="min-h-11 max-h-40 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
              rows={1}
            />
            <Button
              type="submit"
              size="icon"
              disabled={!input.trim() || !!streamingMessage || messagesQuery.isLoading}
            >
              {streamingMessage ? <Loader2 className="animate-spin" /> : <Send />}
            </Button>
          </form>
          <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-muted-foreground">AI can make mistakes. Verify recommendations before using them in official records.</p>
        </div>
      </section>
    </div>
  )
}
