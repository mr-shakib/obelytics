import type { Metadata } from "next"
import { ComplexAttributesClient } from "./complex-attributes-client"

export const metadata: Metadata = { title: "Complex Attributes" }

export default function ComplexAttributesPage() {
  return <ComplexAttributesClient />
}
