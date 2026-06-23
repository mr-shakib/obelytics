"use client"

import { QueryClient, QueryClientProvider, keepPreviousData } from "@tanstack/react-query"
import { useState } from "react"
import { TooltipProvider } from "@/components/ui/tooltip"

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60_000,
            gcTime: 10 * 60_000,
            retry: 1,
            refetchOnWindowFocus: false,
            refetchOnMount: false,
            placeholderData: keepPreviousData,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delay={300}>
        {children}
      </TooltipProvider>
    </QueryClientProvider>
  )
}
