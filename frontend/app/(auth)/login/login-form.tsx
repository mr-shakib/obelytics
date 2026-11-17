"use client"

import { useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Loader2 } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PasswordInput } from "@/components/ui/password-input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardFooter } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { loginApi } from "@/lib/api/auth"
import { useAuthStore } from "@/lib/stores/auth-store"
import { isSectionTeacherView } from "@/lib/navigation"
import { type Dictionary, useI18n } from "@/lib/i18n"

const schema = (t: Dictionary) => z.object({
  email: z.string().email(t.auth.invalidEmail),
  password: z.string().min(1, t.auth.passwordRequired),
})
type FormValues = z.infer<ReturnType<typeof schema>>

export function LoginForm() {
  const { t } = useI18n()
  const router = useRouter()
  const searchParams = useSearchParams()
  const { setAuth } = useAuthStore()
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema(t)) })

  async function onSubmit(values: FormValues) {
    setServerError(null)
    try {
      const { access_token, user, permissions, scope, offering_ids } = await loginApi(
        values.email,
        values.password
      )
      setAuth(access_token, user, { permissions, scope, offering_ids })

      const isStudent = !!user.linked_student_id
      const home = isStudent ? "/my-results" : isSectionTeacherView(permissions) ? "/my-sections" : "/overview"
      const next = searchParams.get("next")
      router.push(!next || next === "/overview" || next === "/" ? home : next)
    } catch (err) {
      setServerError(err instanceof Error ? err.message : t.auth.loginFailed)
    }
  }

  return (
    <Card>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="pt-6 space-y-4">
          {serverError && (
            <Alert variant="destructive">
              <AlertDescription>{serverError}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="email">{t.auth.email}</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@university.edu"
              {...register("email")}
            />
            {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password">{t.auth.password}</Label>
              <Link href="/forgot-password" className="text-xs text-muted-foreground hover:underline">
                {t.auth.forgot}
              </Link>
            </div>
            <PasswordInput
              id="password"
              autoComplete="current-password"
              {...register("password")}
            />
            {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
          </div>
        </CardContent>

        <CardFooter className="flex-col gap-2 pb-6">
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t.auth.signIn}
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}
