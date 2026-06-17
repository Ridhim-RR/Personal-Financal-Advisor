"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Toaster } from "sonner"
import { Sidebar } from "@/components/layout/sidebar"
import { isAuthenticated } from "@/lib/api"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()

  useEffect(() => {
    if (typeof window !== "undefined" && !isAuthenticated()) {
      router.push("/login")
    }
  }, [router])

  if (typeof window !== "undefined" && !isAuthenticated()) return null

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-6 py-8">{children}</div>
      </main>
      <Toaster richColors position="top-right" />
    </div>
  )
}
