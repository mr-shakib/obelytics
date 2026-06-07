import type { Metadata } from "next"
import { ForgotPasswordForm } from "./forgot-password-form"

export const metadata: Metadata = { title: "Reset Password" }

export default function ForgotPasswordPage() {
  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="text-center space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Obelytics</h1>
        <p className="text-sm text-muted-foreground">Reset your password</p>
      </div>
      <ForgotPasswordForm />
    </div>
  )
}
