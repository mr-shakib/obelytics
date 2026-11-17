"use client"

import { LanguageToggle } from "@/components/shared/language-toggle"
import { useI18n } from "@/lib/i18n"

export function LoginHeading() {
  const { t } = useI18n()
  return (
    <div className="text-center space-y-2">
      <h1 className="text-2xl font-bold tracking-tight">Obelytics</h1>
      <p className="text-sm text-muted-foreground">{t.auth.subtitle}</p>
      <LanguageToggle />
    </div>
  )
}
