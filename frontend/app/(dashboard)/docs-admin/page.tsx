import type { Metadata } from "next"

import { DocsAdminClient } from "./docs-admin-client"

export const metadata: Metadata = { title: "Docs Page" }

export default function DocsAdminPage() {
  return <DocsAdminClient />
}
