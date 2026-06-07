"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Bell, CheckCheck } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { useNotificationStore } from "@/lib/stores/notification-store"

type Notification = {
  id: string
  title: string
  body: string
  is_read: boolean
  created_at: string
  link?: string
}

export function NotificationsClient() {
  const qc = useQueryClient()
  const { setUnreadCount } = useNotificationStore()

  const { data: items, isLoading } = useQuery({
    queryKey: queryKeys.notifications.inbox(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/notifications/me" as never)
      return ((data as unknown) as Notification[]) ?? []
    },
  })

  const markAllMutation = useMutation({
    mutationFn: async () => {
      await apiClient.POST("/notifications/read-all" as never, {} as never)
    },
    onSuccess: () => {
      toast.success("All notifications marked as read")
      qc.invalidateQueries({ queryKey: queryKeys.notifications.inbox() })
      qc.invalidateQueries({ queryKey: queryKeys.notifications.unreadCount })
      setUnreadCount(0)
    },
    onError: () => toast.error("Failed to mark notifications"),
  })

  const markOneMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.POST(`/notifications/${id}/read` as never, {} as never)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.notifications.inbox() })
      qc.invalidateQueries({ queryKey: queryKeys.notifications.unreadCount })
    },
  })

  const unread = (items ?? []).filter((n) => !n.is_read).length

  return (
    <div className="space-y-4">
      <PageHeader
        title="Notifications"
        description="Your system notifications and alerts."
        actions={
          unread > 0 ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => markAllMutation.mutate()}
              disabled={markAllMutation.isPending}
            >
              <CheckCheck /> Mark all read
            </Button>
          ) : undefined
        }
      />

      {isLoading && (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => <div key={i} className="h-16 bg-muted animate-pulse rounded-md" />)}
        </div>
      )}

      {!isLoading && (items ?? []).length === 0 && (
        <div className="flex flex-col items-center gap-3 py-12 text-muted-foreground">
          <Bell className="h-8 w-8" />
          <p className="text-sm">No notifications</p>
        </div>
      )}

      <div className="space-y-1">
        {(items ?? []).map((notification) => (
          <div
            key={notification.id}
            className={cn(
              "flex items-start gap-3 p-3 rounded-md border cursor-pointer hover:bg-accent/50 transition-colors",
              !notification.is_read && "bg-accent/20 border-primary/20"
            )}
            onClick={() => {
              if (!notification.is_read) markOneMutation.mutate(notification.id)
            }}
          >
            <div className={cn(
              "w-2 h-2 rounded-full mt-1.5 shrink-0",
              notification.is_read ? "bg-transparent" : "bg-primary"
            )} />
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <p className={cn("text-sm", !notification.is_read && "font-medium")}>{notification.title}</p>
                <span className="text-xs text-muted-foreground shrink-0">
                  {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">{notification.body}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
