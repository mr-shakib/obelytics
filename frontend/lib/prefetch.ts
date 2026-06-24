import { QueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

const prefetchers: Record<string, (qc: QueryClient) => void> = {
  "/courses": (qc) => {
    qc.prefetchQuery({
      queryKey: queryKeys.courses.all,
      queryFn: async () => {
        const { data } = await apiClient.GET("/courses" as never)
        return data
      },
    })
  },
  "/users": (qc) => {
    qc.prefetchQuery({
      queryKey: queryKeys.users.list(),
      queryFn: async () => {
        const { data } = await apiClient.GET("/users" as never)
        return data
      },
    })
  },
  "/program-outcomes": (qc) => {
    qc.prefetchQuery({
      queryKey: queryKeys.poVersions.list(),
      queryFn: async () => {
        const { data } = await apiClient.GET("/po-versions" as never)
        return data
      },
    })
  },
  "/my-sections": (qc) => {
    qc.prefetchQuery({
      queryKey: queryKeys.facultyAssignments.mySections,
      queryFn: async () => {
        const { data } = await apiClient.GET("/faculty-assignments/my-sections" as never)
        return data
      },
    })
  },
  "/result-submissions": (qc) => {
    qc.prefetchQuery({
      queryKey: queryKeys.results.submissions({}),
      queryFn: async () => {
        const { data } = await apiClient.GET("/results" as never)
        return data
      },
    })
  },
  "/notifications": (qc) => {
    qc.prefetchQuery({
      queryKey: queryKeys.notifications.unreadCount,
      queryFn: async () => {
        const { data } = await apiClient.GET("/notifications/me/count" as never)
        return data
      },
    })
  },
}

export function prefetchRoute(qc: QueryClient, href: string) {
  const prefetcher = prefetchers[href]
  if (prefetcher) prefetcher(qc)
}
