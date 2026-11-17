import type { Metadata } from "next"
import { Suspense } from "react"
import { LoginForm } from "./login-form"
import { LoginHeading } from "./login-heading"

export const metadata: Metadata = { title: "Sign In" }

export default function LoginPage() {
  return (
    <div className="w-full max-w-sm space-y-6">
      <LoginHeading />
      <Suspense>
        <LoginForm />
      </Suspense>
    </div>
  )
}
