"use client"

import { useAuthStore } from "@/lib/stores/auth-store"

export function usePermission(code: string): boolean {
  const manifest = useAuthStore((s) => s.manifest)
  if (!manifest) return false
  return manifest.permissions.includes(code)
}

export function useHasAnyPermission(codes: string[]): boolean {
  const manifest = useAuthStore((s) => s.manifest)
  if (!manifest) return false
  return codes.some((c) => manifest.permissions.includes(c))
}

export function usePermissions(): string[] {
  return useAuthStore((s) => s.manifest?.permissions ?? [])
}
