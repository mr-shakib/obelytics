import type { Metadata } from "next"
import { MyProfileClient } from "./my-profile-client"

export const metadata: Metadata = { title: "My Profile" }

export default function MyProfilePage() {
  return <MyProfileClient />
}
