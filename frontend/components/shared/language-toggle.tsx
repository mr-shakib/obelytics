"use client"

import { useEffect } from "react"
import { Languages } from "lucide-react"

import { LOCALES, useI18n, useLocaleStore } from "@/lib/i18n"
import { cn } from "@/lib/utils"

/** Loads the saved language after mount and keeps <html lang> in step with it. */
export function LocaleSync() {
  const locale = useLocaleStore((s) => s.locale)
  useEffect(() => {
    useLocaleStore.persist.rehydrate()
  }, [])
  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])
  return null
}

/** English / বাংলা switch. */
export function LanguageToggle({ className }: { className?: string }) {
  const { t, locale, setLocale } = useI18n()
  return (
    <div
      role="group"
      aria-label={t.common.language}
      className={cn("inline-flex items-center gap-0.5 rounded-md border p-0.5 text-xs", className)}
    >
      <Languages className="mx-1 size-3.5 text-muted-foreground" aria-hidden />
      {LOCALES.map((option) => (
        <button
          key={option.value}
          type="button"
          lang={option.value}
          aria-pressed={locale === option.value}
          onClick={() => setLocale(option.value)}
          className={cn(
            "rounded px-2 py-0.5 transition-colors",
            locale === option.value
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
