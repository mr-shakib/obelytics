import type { Metadata } from "next"
import { ComplexMappingClient } from "@/components/shared/complex-mapping-client"

export const metadata: Metadata = { title: "CO-CA Mappings" }

export default function CoCaMappingPage() {
  return <ComplexMappingClient kind="ca" />
}
