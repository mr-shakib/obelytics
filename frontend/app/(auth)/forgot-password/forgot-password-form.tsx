"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import Link from "next/link"
import { Loader2, CheckCircle2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardFooter } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { requestPasswordReset } from "@/lib/api/auth"

const schema = z.object({ email: z.string().email("Enter a valid email") })
type FormValues = z.infer<typeof schema>

export function ForgotPasswordForm() {
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(values: FormValues) {
    setError(null)
    try {
      await requestPasswordReset(values.email)
      setSent(true)
    } catch {
      setError("Failed to send reset email. Please try again.")
    }
  }

  if (sent) {
    return (
      <Card>
        <CardContent className="pt-6 text-center space-y-3">
          <CheckCircle2 className="mx-auto h-10 w-10 text-green-500" />
          <p className="text-sm text-muted-foreground">
            If an account exists for that email, a reset link has been sent.
          </p>
        </CardContent>
        <CardFooter className="pb-6 justify-center">
          <Link href="/login" className="text-sm text-primary hover:underline">Back to sign in</Link>
        </CardFooter>
      </Card>
    )
  }

  return (
    <Card>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="pt-6 space-y-4">
          {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" autoComplete="email" {...register("email")} />
            {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
          </div>
        </CardContent>
        <CardFooter className="flex-col gap-3 pb-6">
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Send Reset Link
          </Button>
          <Link href="/login" className="text-sm text-muted-foreground hover:underline">Back to sign in</Link>
        </CardFooter>
      </form>
    </Card>
  )
}
