import { redirect } from "next/navigation"

// Root / redirects to the dashboard home inside the (dashboard) route group
export default function RootPage() {
  redirect("/overview")
}
