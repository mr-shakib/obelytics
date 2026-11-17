import type { Metadata } from "next"
import dynamic from "next/dynamic"

const MySkillsClient = dynamic(() => import("./my-skills-client").then(m => m.MySkillsClient))

export const metadata: Metadata = { title: "My Skills" }

export default function MySkillsPage() {
  return <MySkillsClient />
}
