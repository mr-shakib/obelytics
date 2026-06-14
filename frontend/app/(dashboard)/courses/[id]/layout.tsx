import { CourseWorkspaceShell } from "./course-workspace-shell"

export default async function CourseLayout(props: LayoutProps<"/courses/[id]">) {
  const { id } = await props.params
  return <CourseWorkspaceShell id={id}>{props.children}</CourseWorkspaceShell>
}
