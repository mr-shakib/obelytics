import { redirect } from "next/navigation"

export default async function CoursePage({ params }: PageProps<"/courses/[id]">) {
  const { id } = await params
  redirect(`/courses/${id}/overview`)
}
