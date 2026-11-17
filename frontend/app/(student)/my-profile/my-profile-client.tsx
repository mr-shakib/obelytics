"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PasswordInput } from "@/components/ui/password-input"
import { Label } from "@/components/ui/label"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import { useAuthStore } from "@/lib/stores/auth-store"
import { apiClient } from "@/lib/api/client"
import { type Dictionary, useI18n } from "@/lib/i18n"

const passwordSchema = (t: Dictionary) => z.object({
  current_password: z.string().min(1, t.student.profile.required),
  new_password: z.string().min(8, t.student.profile.min8),
  confirm_password: z.string(),
}).refine((d) => d.new_password === d.confirm_password, {
  message: t.student.profile.mismatch,
  path: ["confirm_password"],
})
type PasswordForm = z.infer<ReturnType<typeof passwordSchema>>

export function MyProfileClient() {
  const { user } = useAuthStore()
  const { t } = useI18n()
  const tp = t.student.profile
  const [pwError, setPwError] = useState<string | null>(null)

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema(t)),
  })

  const initials = user
    ? `${user.first_name?.[0] ?? ""}${user.last_name?.[0] ?? ""}`.toUpperCase()
    : "?"

  async function onPasswordChange(values: PasswordForm) {
    setPwError(null)
    try {
      await apiClient.POST("/auth/change-password" as never, {
        body: { current_password: values.current_password, new_password: values.new_password },
      } as never)
      toast.success(tp.changed)
      reset()
    } catch {
      setPwError(tp.failed)
    }
  }

  return (
    <div className="space-y-6 max-w-lg">
      <h1 className="text-2xl font-bold">{tp.title}</h1>

      {/* Identity card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16">
              <AvatarFallback className="text-xl font-bold">{initials}</AvatarFallback>
            </Avatar>
            <div>
              <p className="text-lg font-semibold">{user?.first_name} {user?.last_name}</p>
              <p className="text-sm text-muted-foreground">{user?.email}</p>
              {user?.department && (
                <p className="text-xs text-muted-foreground mt-0.5">{user.department.name}</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Change password */}
      <Card>
        <CardHeader><CardTitle className="text-base">{tp.changePassword}</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onPasswordChange)} className="space-y-4">
            {pwError && <p className="text-sm text-destructive">{pwError}</p>}
            <div className="space-y-2">
              <Label htmlFor="current_password">{tp.current}</Label>
              <PasswordInput id="current_password" autoComplete="current-password" {...register("current_password")} />
              {errors.current_password && <p className="text-xs text-destructive">{errors.current_password.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="new_password">{tp.new}</Label>
              <PasswordInput id="new_password" autoComplete="new-password" {...register("new_password")} />
              {errors.new_password && <p className="text-xs text-destructive">{errors.new_password.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm_password">{tp.confirm}</Label>
              <PasswordInput id="confirm_password" autoComplete="new-password" {...register("confirm_password")} />
              {errors.confirm_password && <p className="text-xs text-destructive">{errors.confirm_password.message}</p>}
            </div>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {tp.update}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
