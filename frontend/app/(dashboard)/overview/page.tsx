"use client"

import { useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { BookCopy, Target, BarChart3, CheckSquare, ClipboardList, Award } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuthStore } from "@/lib/stores/auth-store"
import { usePermission, usePermissions } from "@/hooks/use-permission"
import { isSectionTeacherView } from "@/lib/navigation"

const QUICK_LINKS = [
  { label: "Curricula", href: "/curricula", icon: BookCopy, permission: "curriculum.read", description: "Manage curriculum versions" },
  { label: "Program Outcomes", href: "/program-outcomes", icon: Target, permission: "po.read", description: "Define POs for your programs" },
  { label: "Assessments", href: "/assessments", icon: ClipboardList, permission: "assessment.read", description: "Configure assessments" },
  { label: "Attainment", href: "/attainment", icon: BarChart3, permission: "attainment.read", description: "View CO/PO attainment results" },
  { label: "Approvals", href: "/approvals", icon: CheckSquare, permission: null, description: "Review pending approvals" },
  { label: "Accreditation", href: "/accreditation", icon: Award, permission: "accreditation.cycle.manage", description: "Manage accreditation cycles" },
]

function QuickLinkCard({ item }: { item: typeof QUICK_LINKS[0] }) {
  const hasPermission = usePermission(item.permission ?? "")
  if (item.permission !== null && !hasPermission) return null
  return (
    <Link href={item.href}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <item.icon className="h-5 w-5 text-primary" />
            {item.label}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{item.description}</p>
        </CardContent>
      </Card>
    </Link>
  )
}

export default function OverviewPage() {
  const router = useRouter()
  const user = useAuthStore((s) => s.user)
  const isInitialized = useAuthStore((s) => s.isInitialized)
  const permissions = usePermissions()

  useEffect(() => {
    if (isInitialized && isSectionTeacherView(permissions)) {
      router.replace("/my-sections")
    }
  }, [isInitialized, permissions, router])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Welcome back, {user?.first_name}
        </h1>
        <p className="text-muted-foreground mt-1">Here&apos;s an overview of your OBE workspace.</p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {QUICK_LINKS.map((item) => (
          <QuickLinkCard key={item.href} item={item} />
        ))}
      </div>
    </div>
  )
}
