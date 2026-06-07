"use client"

import { usePermission } from "@/hooks/use-permission"

interface PermissionGateProps {
  permission: string
  fallback?: React.ReactNode
  children: React.ReactNode
}

export function PermissionGate({ permission, fallback = null, children }: PermissionGateProps) {
  const has = usePermission(permission)
  return has ? <>{children}</> : <>{fallback}</>
}
