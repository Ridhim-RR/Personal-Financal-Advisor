"use client"

import { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import * as api from "@/lib/api"
import type { User } from "@/types"

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  const fetchProfile = useCallback(async () => {
    if (!api.isAuthenticated()) { setLoading(false); return }
    try { setUser(await api.getProfile()) }
    catch { setUser(null) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchProfile() }, [fetchProfile])

  const login = async (email: string, password: string) => {
    await api.login(email, password)
    await fetchProfile()
    router.push("/dashboard")
  }

  const register = async (email: string, password: string) => {
    await api.register(email, password)
    await fetchProfile()
    router.push("/dashboard")
  }

  const logout = async () => {
    await api.logout()
    setUser(null)
    router.push("/login")
  }

  return { user, loading, isAuthenticated: api.isAuthenticated(), login, register, logout, fetchProfile }
}
