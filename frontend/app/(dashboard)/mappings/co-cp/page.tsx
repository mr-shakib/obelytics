import type { Metadata } from "next"
import { ComplexMappingClient } from "@/components/shared/complex-mapping-client"

export const metadata: Metadata = { title: "CO-CP Mappings" }

export default function CoCpMappingPage() {
  return <ComplexMappingClient kind="cp" />
}
