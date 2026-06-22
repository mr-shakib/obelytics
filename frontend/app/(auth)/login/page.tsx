import type { Metadata } from "next"
import { Suspense } from "react"
import { LoginForm } from "./login-form"

export const metadata: Metadata = { title: "Sign In" }

export default function LoginPage() {
  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="text-center space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Obelytics</h1>
        <p className="text-sm text-muted-foreground">Sign in to your account</p>
      </div>
      <Suspense>
        <LoginForm />
      </Suspense>
    </div>
  )
}
