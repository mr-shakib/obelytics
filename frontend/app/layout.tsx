import type { Metadata } from "next"
import { Poppins } from "next/font/google"
import { Toaster } from "sonner"
import { Providers } from "@/components/providers"
import { AuthProvider } from "@/components/auth-provider"
import "./globals.css"

const poppins = Poppins({
  variable: "--font-poppins",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
})

export const metadata: Metadata = {
  title: { default: "Obelytics", template: "%s | Obelytics" },
  description: "OBE Accreditation Management Platform",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${poppins.variable} h-full antialiased`}
    >
      <body className="h-full" suppressHydrationWarning>
        <Providers>
          <AuthProvider>
            {children}
          </AuthProvider>
        </Providers>
        <Toaster richColors closeButton position="top-right" />
      </body>
    </html>
  )
}
