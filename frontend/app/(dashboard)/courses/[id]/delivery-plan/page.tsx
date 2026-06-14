import type { Metadata } from "next"
import { CourseDeliveryPlanClient } from "./course-delivery-plan-client"

export const metadata: Metadata = { title: "Delivery Plan" }

export default async function CourseDeliveryPlanPage({ params }: PageProps<"/courses/[id]/delivery-plan">) {
  const { id } = await params
  return <CourseDeliveryPlanClient id={id} />
}
