import type { Metadata } from "next"
import { AcademicTermsClient } from "./academic-terms-client"

export const metadata: Metadata = { title: "Academic Terms" }

export default function AcademicTermsPage() {
  return <AcademicTermsClient />
}
