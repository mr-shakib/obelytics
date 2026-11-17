"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"

import { bn } from "./bn"
import { type Dictionary, en } from "./en"

export type Locale = "en" | "bn"

export const LOCALES: { value: Locale; label: string }[] = [
  { value: "en", label: "English" },
  { value: "bn", label: "বাংলা" },
]

const DICTIONARIES: Record<Locale, Dictionary> = { en, bn }

interface LocaleState {
  locale: Locale
  setLocale: (locale: Locale) => void
}

/**
 * The chosen interface language, kept per browser. Hydration is manual
 * (see LocaleSync) so the first client render matches the server's English
 * render and React never sees a hydration mismatch.
 */
export const useLocaleStore = create<LocaleState>()(
  persist(
    (set) => ({
      locale: "en",
      setLocale: (locale) => set({ locale }),
    }),
    { name: "obelytics-locale", skipHydration: true },
  ),
)

export function useI18n() {
  const locale = useLocaleStore((s) => s.locale)
  const setLocale = useLocaleStore((s) => s.setLocale)
  const t = DICTIONARIES[locale]
  const dateTime = (value: string | number | Date) =>
    new Date(value).toLocaleString(locale === "bn" ? "bn-BD" : undefined)
  return { t, locale, setLocale, dateTime }
}

export type { Dictionary }
